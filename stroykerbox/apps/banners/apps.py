from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class BannersConfig(AppConfig):
    name = 'stroykerbox.apps.banners'
    verbose_name = _('Banners')

    def ready(self):
        from . import signals # noqa
