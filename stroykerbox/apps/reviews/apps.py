from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class ReviewsConfig(AppConfig):
    name = 'stroykerbox.apps.reviews'
    verbose_name = _('Reviews')
