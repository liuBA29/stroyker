from django.db.models.signals import post_save
from django.core.cache import cache
from django.dispatch import receiver

from stroykerbox.apps.banners import BANNERS_FOR_URL_CACHE_PREFIX

from .models import Banner, StroykerBanner


@receiver(post_save, sender=Banner)
@receiver(post_save, sender=StroykerBanner)
def clear_banners_cache(sender, instance, created, **kwargs):
    try:
        # use the django-redis app method
        cache.delete_pattern(f'{BANNERS_FOR_URL_CACHE_PREFIX}:*')
    except AttributeError:
        pass
