from django.template.loader import get_template
from django.conf import settings
from django.contrib.sites.models import Site
from constance import config

from stroykerbox.apps.common.utils import get_notify_location

from .bot import StroykerTelebot


def telebot_send_message(request_instance, template, **kwargs):
    body = get_template(template)

    context = {'object': request_instance, 'form_title': kwargs.get('form_title')}
    context['location'] = get_notify_location(request_instance)
    context['site'] = Site.objects.get_current()
    context['config'] = config

    bot = StroykerTelebot(**kwargs)
    msg = body.render(context)
    return bot.send_message(msg)


def telebot_is_active():
    if settings.DEBUG:
        return False
    return bool(
        (config.TELEBOT_TOKEN or settings.TELEBOT_DEFAULT_TOKEN)
        and (config.TELEBOT_CHAT_ID or config.TELEBOT_CHAT_IDS)
    )
