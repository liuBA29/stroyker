import os
from logging import getLogger
from typing import Any, Optional
import dataclasses
import json

from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models import Model
import requests
from constance import config

from stroykerbox.apps.locations.models import Location

crm_cf_notify_logger = getLogger(settings.CRM_CF_JSON_NOTIFY_LOGGER)


class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any):
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)  # type: ignore
        return super().default(obj)


def send_json_to_url(data_dict: dict, timeout: Optional[int] = None) -> str:
    error_msg = ''

    if not config.CRM_CF_JSON_NOTIFY_URL:
        error_msg = 'FAILED: в настройках не указан URL для отправки данных'
    elif not data_dict:
        error_msg = 'FAILED: нет данных для отправки'
    if error_msg:
        crm_cf_notify_logger.error('error_msg')
        return error_msg

    crm_cf_notify_logger.debug(
        f'Отправка данных на URL: {config.CRM_CF_JSON_NOTIFY_URL}'
    )

    # https://redmine.nastroyker.ru/issues/16755
    try:
        site = Site.objects.get(id=settings.SITE_ID)
    except Exception as e:
        crm_cf_notify_logger.error(str(e))
    else:
        data_dict['siteDomain'] = site.domain

    output = ''

    try:
        if timeout:
            response = requests.post(
                config.CRM_CF_JSON_NOTIFY_URL, json=data_dict, timeout=timeout
            )
        else:
            response = requests.post(config.CRM_CF_JSON_NOTIFY_URL, json=data_dict)
    except Exception as e:
        crm_cf_notify_logger.exception(e)
        output = f'FAILED: {e}'
    else:
        if response.status_code == 200:
            output = 'Отправка прошла успешно. Код ответа: 200.'
            crm_cf_notify_logger.debug(output)
        else:
            output = f'FAILED (код ответа: {response.status_code})'
            crm_cf_notify_logger.error(output)

    return output


def get_logfile_content(logfile_name: str) -> str:
    file_path = os.path.join(settings.LOG_DIR, logfile_name)
    if not os.path.isfile(file_path):
        return f'Файл по пути "{file_path}" не найден.'

    output = ''
    with open(file_path, 'r') as file:
        for num, line in enumerate(file):
            if num:
                output += f'\n\n{line}'

    return output


def get_notify_location(notify_object: Model) -> Optional[Location]:
    """
    Получение региона для отображения в уведомлениях (telegram или email).
    https://redmine.nastroyker.ru/issues/17457
    """
    location = None
    if Location.objects.filter(is_active=True).count() > 1:
        location = (
            getattr(notify_object, 'location', None) or Location.get_default_location()
        )
    return location
