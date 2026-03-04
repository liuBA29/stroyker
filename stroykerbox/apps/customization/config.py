from django.conf import settings


ALLOWED_FONT_EXTENSIONS_LIST = getattr(
    settings, 'ALLOWED_FONT_EXTENSIONS_LIST', ('otf', 'ttf', 'eof', 'woff', 'woff2'))

CUSTOM_STYLES_CACHE_KEY = 'customization_custom_styles'
CUSTOM_SCRIPTS_CACHE_KEY = 'customization_custom_scripts'
