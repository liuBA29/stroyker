from django.apps import AppConfig


class VkMarketConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stroykerbox.apps.vk_market'

    def ready(self):
        from . import signals # noqa
