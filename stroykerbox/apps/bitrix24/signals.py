from logging import getLogger

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType

from stroykerbox.apps.crm import models as crm_models
from stroykerbox.apps.custom_forms.models import CustomFormResult
from stroykerbox.apps.commerce.models import Order
from stroykerbox.apps.commerce.signals import order_paid_by_yookassa

from .utils import b24_is_enabled
from .tasks import sync_with_bitrix24, bitrix24_update_for_yookassa


logger = getLogger('b24')


@receiver(post_save, sender=crm_models.CallMeRequest)
@receiver(post_save, sender=crm_models.FeedbackMessageRequest)
@receiver(post_save, sender=crm_models.FromCartRequest)
@receiver(post_save, sender=crm_models.GiftForPhoneRequest)
@receiver(post_save, sender=CustomFormResult)
def new_crm_request(sender, instance, created, **kwargs):
    if b24_is_enabled():
        content_type = ContentType.objects.get_for_model(instance)
        sync_with_bitrix24.delay(instance.pk, content_type.pk)
        logger.debug(f'sync_with_bitrix24 task is RUNNED for instance {instance}')


@receiver(order_paid_by_yookassa, sender=Order)
def update_order_yookassa_payment(sender: Order, order: Order, **kwargs):
    """
    https://redmine.fancymedia.ru/issues/13218
    """
    if b24_is_enabled():
        bitrix24_update_for_yookassa.delay(order.pk)
        logger.debug(f'bitrix24_update_for_yookassa task is RUNNED for order {order}')
