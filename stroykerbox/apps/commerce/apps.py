from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CommerceConfig(AppConfig):
    name = 'stroykerbox.apps.commerce'
    verbose_name = _('Commerce')

    def ready(self):
        from . import signals # noqa
