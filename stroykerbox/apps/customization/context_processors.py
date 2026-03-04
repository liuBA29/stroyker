from django.conf import settings
from constance import config

from stroykerbox.apps.customization.models import MobileMenuButton


def get_email_logo_url():
    url = settings.BASE_URL
    if config.HEDER_LOGO_FILE:
        url += f'{settings.MEDIA_URL}{config.HEDER_LOGO_FILE}'
    else:
        url += f'{settings.STATIC_URL}images/logo.svg'
    return url


def custom_context(request):
    main_buttons = MobileMenuButton.objects.filter(level=0, active=True)
    return {
        'USE_CUSTOM_HEADERS': config.CUSTOM_HEADER_ID not in ('0', 0),
        'EMAIL_LOGO_URL': get_email_logo_url(),
        'main_buttons': tuple(main_buttons),
    }
