from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stroykerbox.apps.search'
    verbose_name = 'Поиск'

    def ready(self):
        from . import signals # noqa
