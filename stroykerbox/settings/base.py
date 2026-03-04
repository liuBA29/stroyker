import os
import sys

from django.utils.translation import ugettext_lazy as _

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

LOG_DIR = os.path.join(BASE_DIR, '..', 'logs')

CRM_CF_JSON_NOTIFY_LOGGER = 'crm_cf_json_notify'
CRM_CF_JSON_NOTIFY_LOG_FILENAME = 'crm_cf_json_notify.log'

os.makedirs(LOG_DIR, exist_ok=True)

BASE_URL = ''

SECRET_KEY = 'xkz)zl=o@8^_h45+ympuf)53emok@k9f1_brg1b(26py)^r2fg'

TESTING_MODE = 'test' in sys.argv

if TESTING_MODE:
    # provides faster tests
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.MD5PasswordHasher',
    ]


def path(*args):
    """
    Returns an absolute path built from BASE_DIR
    """
    return os.path.join(BASE_DIR, *args)


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Application definition
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'constance',
    'constance.backends.database',
    'filebrowser',
    'pytils',
    'widget_tweaks',
    'django_rq',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django_drf_filepond',
    'mptt',
    'sorl.thumbnail',
    'smart_selects',
    'ckeditor',
    'ckeditor_uploader',
    'uuslug',
    'sekizai',
    'rest_framework',
    'rest_framework.authtoken',
    'import_export',
    'django_geoip',
    'colorfield',
    'compressor',
    'django_unused_media',
    'django_extensions',
    'stroykerbox.apps.users',
    'stroykerbox.apps.catalog',
    'stroykerbox.apps.commerce',
    'stroykerbox.apps.utils',
    'stroykerbox.apps.statictext',
    'stroykerbox.apps.news',
    'stroykerbox.apps.menu',
    'stroykerbox.apps.crm',
    'stroykerbox.apps.articles',
    'stroykerbox.apps.slides',
    'stroykerbox.apps.banners',
    'stroykerbox.apps.seo',
    'stroykerbox.apps.locations',
    'stroykerbox.apps.addresses',
    'stroykerbox.apps.reviews',
    'stroykerbox.apps.subscription',
    'stroykerbox.apps.staticpages',
    'stroykerbox.apps.customization',
    'stroykerbox.apps.scraper',
    'stroykerbox.apps.faq',
    'stroykerbox.apps.custom_forms',
    'stroykerbox.apps.novofon',
    'stroykerbox.apps.floatprice',
    'stroykerbox.apps.amocrm',
    'stroykerbox.apps.bitrix24',
    'stroykerbox.apps.search',
    'stroykerbox.apps.common',
    'stroykerbox.apps.portfolio',
    # 'captcha',
    'django_recaptcha',
    'stroykerbox.apps.ycaptcha',
    'stroykerbox.apps.drf_tracker',
]

RECAPTCHA_PRIVATE_KEY = RECAPTCHA_PUBLIC_KEY = ''
# RECAPTCHA_PRIVATE_KEY = RECAPTCHA_PUBLIC_KEY = None
# SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'stroykerbox.apps.seo.middleware.SeoMiddleware',
    'stroykerbox.apps.locations.middleware.LocationMiddleware',
    'stroykerbox.apps.utils.middleware.LoginRequiredMiddleware',
]

ROOT_URLCONF = 'stroykerbox.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [path('templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'sekizai.context_processors.sekizai',
                'stroykerbox.apps.banners.context_processors.banners',
                'stroykerbox.apps.catalog.context_processors.catalog_context',
                'stroykerbox.apps.customization.context_processors.custom_context',
                'stroykerbox.apps.ycaptcha.context_processors.ycaptcha_context',
                'constance.context_processors.config',
            ],
        },
    },
]

STATICFILES_DIRS = [
    path(BASE_DIR, '..', 'stroyker-k1-html-dev'),
    path(BASE_DIR, 'static'),
]
STATIC_ROOT = path('static_collected')
STATIC_URL = '/static/'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

WSGI_APPLICATION = 'stroykerbox.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'ru'

LOCALE_PATHS = (path('locale'),)

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_L10N = True

USE_TZ = True


LANGUAGES = (
    ('ru', _('Russian')),
    # ('en', _('English')),
)

MEDIA_ROOT = path('media')
# create uploads dir (if not exists)
os.makedirs(path(MEDIA_ROOT, 'uploads'), exist_ok=True)

MEDIA_URL = '/media/'


INVOICE_CSS_PATH = path('static_collected', 'css', 'style.css')

CKEDITOR_UPLOAD_PATH = 'uploads/'
CKEDITOR_IMAGE_BACKEND = "pillow"

CKEDITOR_CONFIGS = {
    'default': {
        'versionCheck': False,
        'removePlugins': 'stylesheetparser',
        'toolbar': None,
        'extraPlugins': ','.join(
            [
                'indent',
                'table',
                'tabletools',
                'tableresize',
                'tableselection',
                'clipboard',
                'image2',
                'uploadimage',
            ]
        ),
        'filebrowserBrowseUrl': '/admin/filebrowser/browse/?pop=3',
        'filebrowserUploadUrl': '/ckeditor/upload/',
        'imageUploadUrl': '/ckeditor/upload/',
        'width': '100%',
        'allowedContent': True,
        'extraAllowedContent': '*(*){*}',
        'entities': False,
        'resize_dir': 'both',
        'iframe_attributes': {},
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

CACHE_NAMESPACE = 'stroykerbox'

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"


# For list_max_show_all in admin
LIST_MAX_SHOW_ALL_FOR_PRODUCT_LIST = 10000

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000


# SORL thumbnail settings
THUMBNAIL_PRESERVE_FORMAT = True
THUMBNAIL_DEBUG = False


# AUTH(users) settings
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'stroykerbox.apps.users.backends.EmailAuthBackend',
]

AUTH_USER_MODEL = 'users.User'
LOGIN_URL = '/account/login/'
LOGIN_REDIRECT_URL = '/user/profile/'
LOGOUT_REDIRECT_URL = '/'

# The model used as the order model.
# This setting is necessary for the CRM app to work properly.
# Like the AUTH_USER_MODEL settings - {app_name}.{model_class}
ORDER_MODEL = 'commerce.Order'

# CONSTANCE settings
CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'
CONSTANCE_IGNORE_ADMIN_VERSION_CHECK = True
CONSTANCE_DATABASE_CACHE_BACKEND = 'default'


SITE_ID = 1

# Django RQ
RQ = {
    'DEFAULT_RESULT_TTL': 172800,  # результы запуска задачь будут сохраняться 2 дня
}

RQ_QUEUES = {
    'default': {
        'HOST': 'redis',
        'PORT': 6379,
        'DB': 3,
        'DEFAULT_TIMEOUT': 360,
    },
    'high': {
        'HOST': 'redis',
        'PORT': 6379,
        'DB': 3,
        'DEFAULT_TIMEOUT': 360,
    },
}
RQ_SHOW_ADMIN_LINK = True

# settings describing the tasks that should be run by the rq_scheduler management
# command. A list of dicts of the form
# {
#    'task': fully qualified path to the task,
#    'args': list of arguments to pass to the task,
#    'kwargs': a dict of kwargs to pass,
#    'interval': seconds between runs,
#    'timeout': task timeout, use -1 to allow unlimited time,
#    'result_ttl': seconds the result is kept,
# }
RQ_PERIODIC = [
    {
        'task': 'stroykerbox.apps.catalog.tasks.sync_moy_sklad_prices',
        'args': [],
        'kwargs': {},
        # 'interval': 'SYNC_PRICES_PERIOD',  # settings name from constance.py
        'timeout': -1,
        'result_ttl': 86400,
    },
    {
        'task': 'stroykerbox.apps.catalog.tasks.sync_moy_sklad_stocks',
        'args': [],
        'kwargs': {},
        # 'interval': 'SYNC_STOCKS_PERIOD',
        'timeout': -1,
        'result_ttl': 86400,
    },
    {
        'task': 'stroykerbox.apps.catalog.tasks.update_yml_file',
        'args': [],
        'kwargs': {},
        # 'interval': 'YML_UPDATE_INTERVAL',
        'timeout': -1,
        'result_ttl': 86400,
    },
    {
        'task': 'stroykerbox.apps.drf_tracker.tasks.clear_api_logs',
        'args': [],
        'kwargs': {},
        'interval': 24,  # in hours
        'timeout': -1,
        'result_ttl': 86400,
    },
]


RQ_PERIODIC_PAYMENT = [
    {
        'task': 'stroykerbox.apps.commerce.tasks.check_payment_yookassa',
        'args': [],
        'kwargs': {},
        # 'interval': 30,  see config.YOOKASSA_CHECK_ORDER_PERIOD
        'timeout': -1,
        'result_ttl': 86400,
    },
]


MANAGERS = {
    ('Alex Jurow', 'ussria@gmail.com'),
    ('Luzhetskiy Dmitry', 'dmitry@fancymedia.ru'),
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        # 'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAdminUser'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}
REST_FRAMEWORK_ALLOWED_IPS = []
REST_FRAMEWORK_ALLOWED_KEYS = ['jf9ossdf_kf23jc_8dGS_*7gf23']

# IPGEO and LOCATIONS
GEOIP_CUSTOM_ISO_CODES = {
    "RU": "Российская Федерация",
}
IPGEOBASE_ALLOWED_COUNTRIES = ['RU']
GEOIP_LOCATION_MODEL = 'stroykerbox.apps.locations.models.Location'

YANDEX_API_KEY = 'c3161078-41ce-4809-936f-dd4c9bcc8a50'

ADMINS = {
    ('Alex Jurow', 'ussria@gmail.com'),
    ('Luzhetskiy Dmitry', 'dmitry@fancymedia.ru'),
}

DEFAULT_FROM_EMAIL = 'sender@stroyker.pro'
EMAIL_HOST = 'smtp.yandex.ru'
EMAIL_PORT = 465
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True
EMAIL_HOST_USER = 'sender@stroyker.pro'
EMAIL_HOST_PASSWORD = 'fqgtovpxqzuvoetl'
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_BACKEND = 'stroykerbox.apps.utils.backends.ConstanceEmailBackend'

FILE_UPLOAD_PERMISSIONS = 0o644


COMPRESS_OUTPUT_DIR = 'cache'
# Сжимать в gz.
COMPRESS_STORAGE = 'compressor.storage.GzipCompressorFileStorage'
COMPRESS_ENABLED = False


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'formatters': {
        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[{server_time}] {message}',
            'style': '{',
        },
        'verbose': {
            'format': '{name} {levelname} {asctime} {module} {lineno} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'INFO',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
        },
        'django.server': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'django.server',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
        },
        'django_error_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 2,
            'filename': os.path.join(LOG_DIR, 'django_errors.log'),
        },
        'moy_sklad_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 2,
            'filename': os.path.join(LOG_DIR, 'moy_sklad.log'),
        },
        'rq_scheduler_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 2,
            'filename': os.path.join(LOG_DIR, 'rq_scheduler.log'),
        },
        'crm_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 2,
            'filename': os.path.join(LOG_DIR, 'crm.log'),
        },
        'smartlombard_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024,  # 1 mgb
            'backupCount': 10,
            'filename': os.path.join(LOG_DIR, 'smartlombard.log'),
        },
        'yml_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024,  # 1 mgb
            'backupCount': 5,
            'filename': os.path.join(LOG_DIR, 'yml_export.log'),
        },
        'novofon_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024,  # 1 mgb
            'backupCount': 5,
            'filename': os.path.join(LOG_DIR, 'novofon.log'),
        },
        'vk_market_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024,  # 10 mgb
            'backupCount': 10,
            'filename': os.path.join(LOG_DIR, 'vk_market.log'),
        },
        'telebot_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024,  # 1 mgb
            'backupCount': 5,
            'filename': os.path.join(LOG_DIR, 'telebot.log'),
        },
        'b24_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024,  # 1 mgb
            'backupCount': 5,
            'filename': os.path.join(LOG_DIR, 'bitrix24.log'),
        },
        'floatprice_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024,  # 1 mgb
            'backupCount': 5,
            'filename': os.path.join(LOG_DIR, 'floatprice.log'),
        },
        'catalog_app_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024,  # 1 mgb
            'backupCount': 5,
            'filename': os.path.join(LOG_DIR, 'catalog.log'),
        },
        'users_app_log_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024,  # 1 mgb
            'backupCount': 5,
            'filename': os.path.join(LOG_DIR, 'users_app.log'),
        },
        'amocrm_logfile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 2,
            'filename': os.path.join(LOG_DIR, 'amocrm.log'),
        },
        'yookassa_logfile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 2,
            'filename': os.path.join(LOG_DIR, 'yookassa.log'),
        },
        'send_mail_logfile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 2,
            'filename': os.path.join(LOG_DIR, 'send_mail.log'),
        },
        'tbank_logfile': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 2,
            'filename': os.path.join(LOG_DIR, 'tbank.log'),
        },
        'ycaptcha_logfile': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 2,
            'filename': os.path.join(LOG_DIR, 'ycaptcha.log'),
        },
        'crm_cf_json_notify_logfile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 2,
            'filename': os.path.join(LOG_DIR, CRM_CF_JSON_NOTIFY_LOG_FILENAME),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['django_error_file', 'mail_admins'],
            'level': 'ERROR',
        },
        'django.server': {
            'handlers': ['django.server'],
            'level': 'INFO',
            'propagate': False,
        },
        # Silence SuspiciousOperation.DisallowedHost exception ('Invalid
        # HTTP_HOST' header messages). Set the handler to 'null' so we don't
        # get those annoying emails.
        'django.security.DisallowedHost': {
            'handlers': ['null'],
            'propagate': False,
        },
        'catalog.moy_sklad.sync': {
            'handlers': ['moy_sklad_log_file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'rq_scheduler': {
            'handlers': ['rq_scheduler_log_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'stroykerbox.apps.crm': {
            'handlers': ['crm_log_file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'stroykerbox.apps.smartlombard': {
            'handlers': ['smartlombard_log_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'yml_export': {
            'handlers': ['yml_log_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'stroykerbox.apps.novofon': {
            'handlers': ['novofon_log_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'stroykerbox.apps.vk_market': {
            'handlers': ['vk_market_log_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'telebot': {
            'handlers': ['telebot_log_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'b24': {
            'handlers': ['b24_log_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'stroykerbox.apps.floatprice': {
            'handlers': ['floatprice_log_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'stroykerbox.apps.catalog': {
            'handlers': ['catalog_app_log_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'stroykerbox.apps.users': {
            'handlers': ['users_app_log_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'stroykerbox.apps.amocrm': {
            'handlers': [
                'amocrm_logfile',
            ],
            'level': 'DEBUG',
        },
        'yookassa': {
            'handlers': [
                'yookassa_logfile',
            ],
            'level': 'DEBUG',
        },
        'mail': {
            'handlers': [
                'send_mail_logfile',
            ],
            'level': 'DEBUG',
        },
        'stroykerbox.apps.smartlombard.tbank': {
            'handlers': [
                'tbank_logfile',
            ],
            'level': 'DEBUG',
        },
        'stroykerbox.apps.ycaptcha': {
            'handlers': [
                'ycaptcha_logfile',
            ],
            'level': 'ERROR',
        },
        CRM_CF_JSON_NOTIFY_LOGGER: {
            'handlers': [
                'crm_cf_json_notify_logfile',
            ],
            'level': 'DEBUG',
        },
    },
}

# default telegram bot ('stroyker')
TELEBOT_DEFAULT_TOKEN = '5319618547:AAFjr7x2vD7gxEC-X8k7VFKLb7A71kcJCXM'

FILEBROWSER_EXTENSIONS = {
    'Image': ('.jpg', '.jpeg', '.gif', '.png', '.tif', '.tiff', '.webp'),
    'Misc': ('.svg', '.apk', '.zip', 'json', '.css', '.js', '.htm', '.html'),
    'Document': ('.pdf', '.doc', '.docx', '.rtf', '.txt', '.xls', '.xlsx', '.csv'),
    'Video': (
        '.mov',
        '.mp4',
        '.m4v',
        '.webm',
        '.wmv',
        '.mpeg',
        '.mpg',
        '.avi',
        '.rm',
        '.glb',
    ),
    'Audio': ('.mp3', '.wav', '.aiff', '.midi', '.m4p'),
}
FILEBROWSER_SELECT_FORMATS = {
    'file': ['Image', 'Misc', 'Document', 'Video', 'Audio'],
    'image': ['Image'],
    'document': ['Document'],
    'media': ['Video', 'Audio'],
}
FILEBROWSER_MAX_UPLOAD_SIZE = 50 * 1024 * 1024

APPS_ORDER = {
    'constance': 'a',
    'crm': 'b',
    'commerce': 'c',
    'catalog': 'd',
    'staticpages': 'e',
    'statictext': 'f',
    'news': 'g',
    'articles': 'i',
    'sites': 'j',
    'django_rq': 'k',
    'redirects': 'l',
    'scraper': 'm',
    'authtoken': 'n',
    'faq': 'o',
    'filebrowser': 'p',
    'addresses': 'q',
    'custom_forms': 'r',
    'menu': 's',
    'reviews': 't',
    'subscription': 'u',
    'auth': 'v',
    'locations': 'w',
    'seo': 'x',
    'banners': 'y',
    'slides': 'z',
    'customization': 'za',
}

# path relative for MEDIA dir
YML_EXPORT_CATALOG = path(MEDIA_ROOT, 'yml_export')
YML_EXPORT_CATALOG_URL = f'{MEDIA_URL}yml_export/'
YML_EXPORT_FILE_PATH = path(YML_EXPORT_CATALOG, 'catalog_export.yml')


SHELL_PLUS_IMPORTS = []

DJANGO_DRF_FILEPOND_UPLOAD_TMP = os.path.abspath(
    path(MEDIA_ROOT, 'filepond', 'uploaded_files')
)
DJANGO_DRF_FILEPOND_FILE_STORE_PATH = os.path.abspath(
    path(MEDIA_ROOT, 'filepond', 'stored_uploads')
)
DJANGO_DRF_FILEPOND_STORAGES_BACKEND = (
    'stroykerbox.apps.custom_forms.storage.FilePondStorage'
)
DJANGO_DRF_FILEPOND_ALLOW_EXTERNAL_UPLOAD_DIR = True


SECURE_REFERRER_POLICY = 'no-referrer-when-downgrade'

try:
    # Локальная разработка: если есть constants_local.py — используем его (файл в .gitignore).
    # У заказчика этого файла нет, подхватится их settings/constants.py.
    from . import constants_local
    import sys
    sys.modules['stroykerbox.settings.constants'] = constants_local
    from .constants_local import *  # noqa
except ImportError:
    try:
        from .constants import *  # noqa
    except ImportError:
        pass
