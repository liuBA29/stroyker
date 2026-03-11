# mypy: ignore-errors
# flake8: noqa
from .base import *

from django.utils.translation import ugettext_lazy as _


DEBUG = True

# Переключение дизайна 8 марта (шапка, подвал, главная).
# По умолчанию включено в base.py. Чтобы ВЫКЛЮЧИТЬ у себя — раскомментируй строку ниже.
# USE_8MARCH_HEADER_FOOTER = False

# Страница «как у заказчика»: localhost/prod29/ показывает главную в СТАРОМ дизайне (без 8 марта).
# Нужна, чтобы смотреть меню/контент из админки и переносить в дизайн 8 марта. На проде не задавать — тогда /prod29/ будет дублировать главную в новом дизайне.
FORCE_OLD_DESIGN_PATH = 'prod29'

BASE_URL = 'http://stroykerbox.local'

RQ_PERIODIC = []

INVOICE_CSS_PATH = path('static', 'css', 'style.css')

ADMIN__PRODUCT_PER_PAGE = 10
# INTERNAL_IPS = ['*',]

INSTALLED_APPS += [
    'django.contrib.redirects',
    # 'stroykerbox.apps.smartlombard',
    # 'stroykerbox.apps.booking',
    # 'stroykerbox.apps.vk_market',
]

# MIDDLEWARE += ['django.contrib.redirects.middleware.RedirectFallbackMiddleware']
MIDDLEWARE += ['stroykerbox.apps.utils.middleware.CustomRedirectFallbackMiddleware']


ALLOWED_HOSTS = ['*', '127.0.0.1', 'stroykerbox.local']

# Constance в dev: без кэша Redis при сохранении, иначе "signal only works in main thread"
CACHES['constance_dummy'] = {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}
CONSTANCE_DATABASE_CACHE_BACKEND = 'constance_dummy'

# Дефолты Constance для локального Docker (пустая БД до loaddata).
# Используется только при settings.dev. У заказчика — settings.luciano, этот блок не трогаем.
# Сначала явные значения, затем подгружаем остальные из фикстуры
_constance_defaults = {
    'INVOICING_DISPLAY_NAME': 'Счёт',
    'CARD_UPON_RECEIPT_DISPLAY_NAME': 'Картой при получении',
    'CASH_UPON_RECEIPT_DISPLAY_NAME': 'Наличными при получении',
    'ONLINE_ON_SITE_DISPLAY_NAME': 'Онлайн на сайте',
    'CREDIT_DISPLAY_NAME': 'В кредит',
    'YOOKASSA_DISPLAY_NAME': 'ЮKassa',
    'STROYKER_BANNERS_LIMIT_FOR_URL': 5,
    'IMPORT__SKIP_UNCHANGED': True,
    'IMPORT__SKIP_DIFF': True,
    'IMPORT__REPORT_SKIPPED': False,
    'SITE_NAME': 'Luciano Flowers',
    'DEFAULT_FROM_EMAIL': 'noreply@localhost',
    'BANNERS_NOTIFY_DAYS_BEFORE_EXPIRE': 7,
    'NEWS_PER_PAGE': 10,
    'ARTICLES_SECTION_NAME': 'Статьи',
    'CATALOG_MENU_TITLE': 'Каталог',
    'SEARCH__QUERY_MIN_CHARS': 2,
    'SEARCH_INPUT_PLACEHOLDER': 'Поиск',
    'PRODUCT_NOT_AVAIBLE_STATUS_NAME': 'Нет в наличии',
    'PRICE_DEFAULT_LABEL': 'Цена',
    'ONLINE_PRICE_LABEL_TEXT': 'Цена',
    'ADD_TO_CART_BTN_LABEL': 'В корзину',
    'EMPTY_CART_MESSAGE': 'Корзина пуста',
    'ADMIN__PRODUCT_PER_PAGE': 10,
    'PRODUCTS_COUNT_ON_PAGE': 10,
    'ADMIN_SITE_HEADER': 'Luciano Flowers',
    'ADMIN_SITE_META_TITLE': 'Luciano Flowers',
    'GLOBAL_ACCESS_AUTHORIZED_ONLY': False,
    'PRODUCTS_MERGE_BY_MODIFICATION_CODE': False,
    'IMPORT__CREATE_IF_NOT_EXISTS': False,
    'SIMPLE_CART_MODE': False,
    'DELIVERY_PICUP_PAYMENT_METHODS': '[]',
    'DELIVERY_TOADDRESS_PAYMENT_METHODS': '[]',
    'DELIVERY_TOTC_PAYMENT_METHODS': '[]',
    'DELIVERY_METHODS': '[]',
    'PAYMENT_METHODS': '[]',
    'DELIVERY_PICUP_COST': 0,
    'DELIVERY_TOADDRESS_COST': 0,
    'DELIVERY_TOTC_COST': 0,
    'DELIVERY_PICKUP_DISPLAY_NAME': '',
    'DELIVERY_TOADDRESS_DISPLAY_NAME': '',
    'DELIVERY_TOTC_DISPLAY_NAME': '',
    'INVOICE_PDF_ANON_ALLOWED': False,
    'YAMAP_DEFAULT_CENTER_LATITUDE': 53.20,
    'YAMAP_DEFAULT_CENTER_LONGITUDE': 50.17,
    'CATALOG_MENU_ITEMS_LIMIT': 0,
    'CATALOG_SHOW_CHILDS_IN_PARENT': False,
    'CATALOG_PRODUCT_LIST_ON_INDEX_PAGE': False,
    'PRODUCT_AVAIL_LABEL_VARIANT': '1',
    'PRODUCT_SHOW_AVAIL_STOCKS': False,
    'CATEGORY_PRODUCTS_PER_ROW': 3,
    'PRICE_WITH_PENNIES': False,
    'SLIDER_CONSTRUCTOR__DATA_SLIDES': 1,
    'SLIDER_CONSTRUCTOR__DATA_SM_SLIDES': 1,
    'SLIDER_CONSTRUCTOR__DATA_MD_SLIDES': 1,
    'SLIDER_CONSTRUCTOR__DATA_LG_SLIDES': 1,
    'SLIDER_CONSTRUCTOR__DATA_XL_SLIDES': 1,
    'RELATED_PRODUCTS_DISPLAY_VARIANT': '',
    'RELATED_PRODUCTS_SHOW_NOT_AVAIBLE': False,
    'PERSONAL_PRICE_LABEL': '',
    'PRODUCT_TEASER_VARIANT': '0',
    'DISPLAY_TAG_CONTAINERS': '[]',
    'CAPTCHA_MODE': 'google',
    'YCAPTCHA_CLIENT_KEY': '',
    'YCAPTCHA_SERVER_KEY': '',
    'RECAPTCHA_REGISTRATION_FORM': False,
    'RECAPTCHA_FEEDBACK_FORM': False,
    'RECAPTCHA_CALLME_FORM': False,
    'RECAPTCHA_CART_FORM': False,
    'CAPTCHA_USE_FOR_BOOKING_FORM': False,
    'USE_8MARCH_HEADER_FOOTER': False,
}
import json
import os as _os
_fixture_path = _os.path.join(_os.path.dirname(__file__), '..', 'apps', 'utils', 'fixtures', 'default_data.json')
if _os.path.isfile(_fixture_path):
    try:
        with open(_fixture_path, 'r', encoding='utf-8') as _f:
            for _item in json.load(_f):
                if _item.get('model') == 'constance.constance':
                    _k = _item.get('fields', {}).get('key')
                    _v = _item.get('fields', {}).get('value')
                    if _k and _k not in _constance_defaults:
                        if isinstance(_v, bool):
                            _constance_defaults[_k] = _v
                        elif isinstance(_v, (int, float)):
                            _constance_defaults[_k] = _v
                        else:
                            _constance_defaults[_k] = '' if _v is None else ''
    except Exception:
        pass
# Если есть дамп Constance с сервера — подхватываем все ключи (значения потом из БД после loaddata)
_dump_path = _os.path.join(_os.path.dirname(__file__), '..', 'apps', 'utils', 'fixtures', 'constance_dump.json')
if _os.path.isfile(_dump_path):
    try:
        with open(_dump_path, 'r', encoding='utf-8') as _f:
            for _item in json.load(_f):
                if _item.get('model') == 'constance.constance':
                    _k = _item.get('fields', {}).get('key')
                    _v = _item.get('fields', {}).get('value')
                    if _k and _k not in _constance_defaults:
                        if isinstance(_v, bool):
                            _constance_defaults[_k] = _v
                        elif isinstance(_v, (int, float)):
                            _constance_defaults[_k] = _v
                        else:
                            _constance_defaults[_k] = ''
    except Exception:
        pass
CONSTANCE_CONFIG = {k: (v, '') for k, v in _constance_defaults.items()}

if DEBUG:
    import os  # only if you haven't already imported this
    import socket  # only if you haven't already imported this

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + [
        "127.0.0.1",
        "10.0.2.2",
    ]


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'stroykerbox',
        'USER': 'stroykerbox',
        'PASSWORD': 'stroykerbox',
        'HOST': 'db',  # имя сервиса в docker-compose
        'PORT': '5432',
    }
}


DEBUG_TOOLBAR_CONFIG = {
    # Toolbar options
    "SHOW_TOOLBAR_CALLBACK": lambda x: True,
    # 'RESULTS_CACHE_SIZE': 3,
    'SHOW_COLLAPSED': True,
    # Panel options
    'SQL_WARNING_THRESHOLD': 100,  # milliseconds
    'SHOW_TEMPLATE_CONTEXT': True,
}

LOGGING['loggers']['catalog.moy_sklad.sync'] = {  # typing: ignore
    'handlers': ['console'],
    'level': 'DEBUG',
    'propagate': False,
}

EMAIL_FILE_PATH = path('test_email')
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'

RECAPTCHA_TESTING = True
RECAPTCHA_PRIVATE_KEY = RECAPTCHA_PUBLIC_KEY = ''
SILENCED_SYSTEM_CHECKS = ['django_recaptcha.recaptcha_test_key_error']

SHELL_PLUS_IMPORTS = [
    # 'from stroykerbox.apps.vk_market.vk import VKMarket',
    # 'from stroykerbox.apps.novofon.helper import Novofon',
    # 'from stroykerbox.apps.floatprice import tasks as fp_tasks',
    'from stroykerbox.apps.amocrm import amocrm as amo',
    # 'from stroykerbox.apps.common.services import FrontpageParser, CommonChecker',
    'from constance import config',
    # 'from stroykerbox.apps.smartlombard.tbank.services.smartlombard_api import SmartlombardAPI',
    # 'from stroykerbox.apps.smartlombard.tbank.services.tbank_api import TBankAPI',
    'from stroykerbox.apps.crm.tasks import process_new_callme_request, process_new_feedback_message_request',
]
