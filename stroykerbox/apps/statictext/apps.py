from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class StatictextConfig(AppConfig):
    name = 'stroykerbox.apps.statictext'
    verbose_name = _('Static text')

    def ready(self):
        from . import signals # noqa
