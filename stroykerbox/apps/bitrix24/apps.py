from django.apps import AppConfig


class Bitrix24Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stroykerbox.apps.bitrix24'
    verbose_name = 'Bitrix24'


    def ready(self):
        from . import signals # noqa
