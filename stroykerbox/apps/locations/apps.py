from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class LocationsConfig(AppConfig):
    name = 'stroykerbox.apps.locations'
    verbose_name = _('Locations')

    def ready(self):
        from . import signals # noqa
