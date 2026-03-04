from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class StaticpagesConfig(AppConfig):
    name = 'stroykerbox.apps.staticpages'
    verbose_name = _('Static pages')

    def ready(self):
        from . import signals # noqa
