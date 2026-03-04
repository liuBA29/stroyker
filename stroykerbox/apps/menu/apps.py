from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class MenuConfig(AppConfig):
    name = 'stroykerbox.apps.menu'
    verbose_name = _('Menu')
