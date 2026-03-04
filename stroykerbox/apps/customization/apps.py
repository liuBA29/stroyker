from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CustomizationConfig(AppConfig):
    name = 'stroykerbox.apps.customization'
    verbose_name = _('Customization')

    def ready(self):
        from . import signals # noqa
