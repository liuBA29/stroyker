from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class UtilsConfig(AppConfig):
    name = 'stroykerbox.apps.utils'
    verbose_name = _('Common Utils')

    def ready(self):
        from . import signals # noqa
