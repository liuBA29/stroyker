from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from constance import config

from .tasks import send_user_activation_notify, send_user_activation_notify_manager
# from .tasks import send_user_activation_notify, new_registration_notify_manager


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def on_user_save(sender, instance, created=False, **kwargs):
    # Про "автоакцивацию" и реакцию/телодвижения на данную настройку тут:
    # https://redmine.fancymedia.ru/issues/10881
    if created:
        Token.objects.create(user=instance)
    elif instance and instance.is_active and hasattr(
            instance, '_original_is_active') and not instance._original_is_active:

        # У пользователя изменился статус "активности"
        # Если автоактивация отключена - пользователь активирован
        # менеджером в админке. Отправляем мыл активированному пол-лю.
        if not config.USERS_AUTOACTIVATION:
            send_user_activation_notify.delay(instance)
        else:
            # При включенной автоактивации считаем, что это
            # пользователь самоактивировался, и уведомляем о том менеджера.
            send_user_activation_notify_manager.delay(instance)
