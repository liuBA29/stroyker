from typing import Optional

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django_rq import job
from constance import config

from .models import B24Log
from .services import B24


@job('high')
def sync_with_bitrix24(object_id, content_type_id):
    try:
        content_type = ContentType.objects.get(id=content_type_id)
        Model = content_type.model_class()
        instance = Model.objects.get(pk=object_id)
    except Model.DoesNotExist:
        return f'FAIL! Обьекта с ID {object_id} не найдено.'
    except Exception as e:
        return f'FAIL! {e}'

    json_data = instance.b24_fields
    response = B24().add_lead(json_data)

    if response.status_code == 200:
        r_json = response.json()
        b24_id = r_json.get('result')
        B24Log.objects.create(
            lead_id=b24_id, content_type=content_type, object_id=object_id, data=r_json
        )
        return 'ОК'
    else:
        return f'FAIL! Статус ответа со стороны B24: {response.status_code}'


@job('high')
def bitrix24_update_for_yookassa(order_id: int) -> Optional[str]:
    """
    https://redmine.fancymedia.ru/issues/13218
    """
    if not config.B24_YOOKASSA_FIELD_NAME:
        return 'FAIL! Не указано имя поля для суммы платежа Yookassa.'

    try:
        FromCartRequest = apps.get_model('crm.FromCartRequest')
    except Exception as e:
        return f'ERROR: {e}'

    crm_obj = FromCartRequest.objects.filter(order_id=order_id).first()

    if crm_obj and (log := B24Log.objects.filter(content_object=crm_obj).first()):
        fields_data = {config.B24_YOOKASSA_FIELD_NAME: log.get_b24_yookassa_amount()}
        response = B24().update_lead(log.lead_id, fields_data)

        if hasattr(response, 'json'):
            log.write_to_log(response.json())
        if response.status_code == 200:
            return 'ОК'
        else:
            return f'FAIL! Статус ответа со стороны B24: {response.status_code}'
    return None
