from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SeoConfig(AppConfig):
    name = 'stroykerbox.apps.seo'
    verbose_name = _('SEO')

    def ready(self):
        from . import signals # noqa
