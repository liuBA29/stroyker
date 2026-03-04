from django.apps import AppConfig


class AmocrmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stroykerbox.apps.amocrm'
    verbose_name = 'AMOCRM'

    def ready(self):
        from . import signals # noqa
