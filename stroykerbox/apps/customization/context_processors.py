from django.conf import settings
from constance import config

from stroykerbox.apps.customization.models import MobileMenuButton


def _use_8march_header_footer(request=None):
    """При request: если path = prod29 или совпадает с FORCE_OLD_DESIGN_PATH — показываем старый дизайн. Иначе — settings или Constance."""
    try:
        if request is not None:
            req_path = (request.path or '').strip('/')
            # Всегда показывать старый дизайн на /prod29/ (скрытая страница «как у заказчика»)
            if req_path == 'prod29':
                return False
            path_val = getattr(settings, 'FORCE_OLD_DESIGN_PATH', None)
            if path_val:
                check_path = (path_val if isinstance(path_val, str) else str(path_val)).strip('/')
                if req_path == check_path:
                    return False
        if hasattr(settings, 'USE_8MARCH_HEADER_FOOTER'):
            return bool(settings.USE_8MARCH_HEADER_FOOTER)
        return getattr(config, 'USE_8MARCH_HEADER_FOOTER', False)
    except Exception:
        # Не ронять сайт при ошибке Constance/БД — по умолчанию новый дизайн
        return True


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
        'use_8march_header_footer': _use_8march_header_footer(request),
    }
