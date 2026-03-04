from logging import getLogger
from typing import Optional

from django.template.loader import get_template
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.utils.html import strip_tags

from django_rq import job
from constance import config

from stroykerbox.apps.commerce.models import Order
from stroykerbox.apps.telebot.helpers import telebot_is_active, telebot_send_message
from stroykerbox.apps.api.crm.serializers import CrmRequestBaseSerializer
from stroykerbox.apps.common.utils import send_json_to_url, get_notify_location

from .models import (
    CallMeRequest,
    FeedbackMessageRequest,
    CrmRequestBase,
    GiftForPhoneRequest,
)

email_logger = getLogger('mail')

MAIL_DEFAULT_SUBJECT = 'Новый запрос'


def notify_managers(
    request_instance,
    template,
    subject: Optional[str] = None,
) -> None:
    # send email notification to manager
    body = get_template(template)
    context = {'object': request_instance}
    context['location'] = get_notify_location(request_instance)
    context['site'] = Site.objects.get_current()
    recipient_list = [e.strip() for e in config.MANAGER_EMAILS.split(',')]
    mail_subject = subject or MAIL_DEFAULT_SUBJECT
    mail_subject = strip_tags(mail_subject).replace('\n', ' ')

    if domain := getattr(context['site'], 'domain', None):
        mail_subject += f' с сайта {domain}'

    context['mail_header'] = mail_subject

    html = body.render(context)

    try:
        send_mail(
            subject=mail_subject,
            message=strip_tags(html),
            html_message=html,
            from_email=config.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
    except Exception as e:
        email_logger.exception(e)


@job('high')
def process_new_from_cart_request_created(order_pk: int | str):
    """
    Actions when creating the new order from cart request.
    """
    if telebot_is_active() and config.TELEBOT_ORDER_FORM_ENABLED:
        try:
            order = Order.objects.get(pk=order_pk)
        except Order.DoesNotExist:
            return

        if config.SIMPLE_CART_MODE:
            template = 'crm/telebot/new-order-notification-simple-mode.html'
        else:
            template = 'crm/telebot/new-order-notification.html'

        return telebot_send_message(order, template)


@job('high')
def process_new_callme_request(instance_pk: int | str):
    """
    Actions when creating the new call-me request.
    """
    try:
        instance = CallMeRequest.objects.get(pk=instance_pk)
    except CallMeRequest.DoesNotExist:
        return f'CallMeRequest object with ID {instance_pk} not found.'

    if telebot_is_active() and config.TELEBOT_CALLME_FORM_ENABLED:
        telebot_send_message(
            instance, 'crm/telebot/new-callme-request-notification.html'
        )

    template = 'crm/email/new-callme-request-notification.html'
    subject = 'Запрос обратного звонка'
    notify_managers(instance, template, subject=subject)


@job('high')
def process_new_feedback_message_request(instance_pk: int | str) -> Optional[str]:
    """
    Actions when creating the new feedback message request.
    """
    try:
        instance = FeedbackMessageRequest.objects.get(pk=instance_pk)
    except CallMeRequest.DoesNotExist:
        return f'FeedbackMessageRequest object with ID {instance_pk} not found.'

    form_title_str = getattr(config, 'FEEDBACK_FORM_TITLE', '')
    form_title = strip_tags(form_title_str).replace('\n', ' ')

    if telebot_is_active() and config.TELEBOT_FEEDBACK_FORM_ENABLED:
        telebot_send_message(
            instance,
            'crm/telebot/new-feedback-msg-request-notification.html',
            form_title=form_title,
        )

    template = 'crm/email/new-feedback-msg-request-notification.html'
    subject = f'Новое сообщение с формы "{form_title}"'
    notify_managers(instance, template, subject=subject)


@job('high')
def process_new_giftforphone_request(instance_pk: int | str) -> None:
    if telebot_is_active() and config.TELEBOT_FEEDBACK_FORM_ENABLED:
        try:
            instance = GiftForPhoneRequest.objects.get(pk=instance_pk)
        except GiftForPhoneRequest.DoesNotExist:
            return
        telebot_send_message(
            instance, 'crm/telebot/new-giftforphone-request-notification.html'
        )


@job(
    'high', result_ttl=86400 * 7
)  # результат выполнения(в админке) сохраняется на 7 дней
def send_new_crm_json_notify(instance_pk: int | str) -> Optional[str]:
    """
    https://redmine.nastroyker.ru/issues/16265
    """
    try:
        obj = CrmRequestBase.objects.get(pk=instance_pk)
    except CrmRequestBase.DoesNotExist:
        return None

    serializer = CrmRequestBaseSerializer(obj)
    return send_json_to_url(serializer.data)
