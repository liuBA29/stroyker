from typing import Optional

from django_rq import job
from constance import config

from stroykerbox.apps.telebot.helpers import telebot_send_message, telebot_is_active
from stroykerbox.apps.crm.tasks import notify_managers
from stroykerbox.apps.common.utils import send_json_to_url

from .models import CustomFormResult


@job('high')
def process_new_results_from_custom_form(object_pk: int) -> Optional[str]:
    try:
        obj = CustomFormResult.objects.get(pk=object_pk)
    except CustomFormResult.DoesNotExist:
        return f'Объект с ID {object_pk} не найден.'

    if telebot_is_active() and config.TELEBOT_CUSTOM_FORM_ENABLED:
        telebot_send_message(
            obj,
            'custom_forms/telebot/new-results.html',
            chat_id=obj.form.telegram_chat_id,
        )

    template = 'custom_forms/email/new-results.html'
    subject = f'Новое сообщение с формы "{obj.form.title}"'
    notify_managers(obj, template, subject=subject)

    # https://redmine.nastroyker.ru/issues/16265
    if config.CRM_CF_JSON_NOTIFY_URL:
        if data := obj.to_dict():
            output = send_json_to_url(data)
            return output
