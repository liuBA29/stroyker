from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class CrmConfig(AppConfig):
    name = 'stroykerbox.apps.crm'
    verbose_name = _('CRM')

    def ready(self):
        from . import signals # noqa
