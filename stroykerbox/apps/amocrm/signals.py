import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from constance import config
from stroykerbox.apps.crm import models as crm_models
from stroykerbox.apps.custom_forms.models import CustomFormResult

from .amocrm import AMOCrmDisabledException, Amo

logger = logging.getLogger(__name__)


@receiver(post_save, sender=crm_models.CallMeRequest)
@receiver(post_save, sender=crm_models.FeedbackMessageRequest)
@receiver(post_save, sender=crm_models.FromCartRequest)
@receiver(post_save, sender=crm_models.GiftForPhoneRequest)
@receiver(post_save, sender=CustomFormResult)
def new_crm_request(sender, instance, created, **kwargs):
    if created and config.AMOCRM_ENABLED:
        try:
            amo = Amo(instance)
            amo.add_lead()
        except AMOCrmDisabledException:
            logger.error(
                'Для интеграции с AMOCRM не указаны все необходимые настройки.')
        except Exception as e:
            logger.exception(e)
        else:
            logger.info(
                f'Новый запрос с {instance} успешно отправлен на AMOCRM.')
