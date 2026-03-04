from django.db.models.signals import post_save
from django.dispatch import receiver

from constance import config
from stroykerbox.apps.commerce.models import OrderNew
from stroykerbox.apps.commerce.signals import new_order_created

from . import models, tasks


def _get_username(order):
    if order.user:
        return order.user.name or order.user.email
    elif hasattr(order, 'ordercontactdata'):
        return order.ordercontactdata.name
    return getattr(order.delivery, 'name', '')


def new_crm_request_base_created_notify(instance: models.CrmRequestBase) -> None:
    """
    https://redmine.nastroyker.ru/issues/16265
    """
    if getattr(config, 'CRM_CF_JSON_NOTIFY_URL', None):
        tasks.send_new_crm_json_notify.delay(instance.pk)


@receiver(new_order_created, sender=OrderNew)
def new_regular_mode_order_from_cart_created(sender, order, **kwargs):
    """
    For normal cart mode only.
    The request object, as the CRM item, is created only when
    creating an order through the cart (not manually by a manager).

    """
    if config.SIMPLE_CART_MODE or not order.from_cart:
        return

    if not models.FromCartRequest.objects.filter(order=order).exists():
        phone = order.user.phone if order.user is not None else order.delivery.phone
        crm_obj = models.FromCartRequest.objects.create(
            order=order, name=_get_username(order), phone=phone, location=order.location
        )
        tasks.process_new_from_cart_request_created.delay(order.pk)
        new_crm_request_base_created_notify(crm_obj)


@receiver(new_order_created, sender=OrderNew)
def new_simple_mode_order_from_cart_created(sender, order, **kwargs):
    """
    For simplefied cart mode only.
    """
    if (
        not config.SIMPLE_CART_MODE
        or not order.from_cart
        or not hasattr(order, 'ordercontactdata')
    ):
        return

    if not models.FromCartRequest.objects.filter(order=order).exists():
        crm_obj = models.FromCartRequest.objects.create(
            order=order,
            name=order.ordercontactdata.name,
            phone=order.ordercontactdata.phone,
            location=order.location,
        )
        tasks.process_new_from_cart_request_created.delay(order.pk)
        new_crm_request_base_created_notify(crm_obj)


@receiver(post_save, sender=models.CallMeRequest)
def new_callme_request_created(sender, instance, created, **kwargs):
    if created:
        tasks.process_new_callme_request.delay(instance.pk)
        new_crm_request_base_created_notify(instance)


@receiver(post_save, sender=models.FeedbackMessageRequest)
def new_feedback_message_request_created(sender, instance, created, **kwargs):
    if created:
        tasks.process_new_feedback_message_request.delay(instance.pk)
        new_crm_request_base_created_notify(instance)


@receiver(post_save, sender=models.GiftForPhoneRequest)
def new_giftforphone_request_created(sender, instance, created, **kwargs):
    if created:
        tasks.process_new_giftforphone_request(instance.pk)
        new_crm_request_base_created_notify(instance)
