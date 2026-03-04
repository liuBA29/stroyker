from django.conf import settings
from constance import config


def b24_is_enabled() -> bool:
    return all((not settings.DEBUG, config.B24_ENABLED, config.B24_WEBHOOK_URL))
