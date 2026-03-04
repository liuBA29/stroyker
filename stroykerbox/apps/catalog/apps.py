from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CatalogConfig(AppConfig):
    name = 'stroykerbox.apps.catalog'
    verbose_name = _('Catalog')

    def ready(self):
        from . import signals # noqa

