from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class FaqConfig(AppConfig):
    name = 'stroykerbox.apps.faq'
    verbose_name = _('FAQ')
