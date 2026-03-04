from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SubscriptionConfig(AppConfig):
    name = 'stroykerbox.apps.subscription'
    verbose_name = _('Subscription')
