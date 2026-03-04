from django.dispatch import receiver
from django.db.models.signals import post_save

from stroykerbox.apps.telebot.helpers import telebot_is_active, telebot_send_message

from .models import ItemReserve


@receiver(post_save, sender=ItemReserve)
def new_request_created(sender, instance, created, **kwargs):
    if telebot_is_active and not instance.no_notify:
        template = 'booking/telebot/notify.html'
        telebot_send_message(instance, template)
