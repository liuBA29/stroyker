from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CustomFormsConfig(AppConfig):
    name = 'stroykerbox.apps.custom_forms'
    verbose_name = _('Custom forms')

    def ready(self):
        from . import signals # noqa
