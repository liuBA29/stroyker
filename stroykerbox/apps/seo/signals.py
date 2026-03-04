from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from .views import ROBOT_TXT_CACHE_KEY_PREFIX, get_robots_txt_content
from .models import RobotsTxt, MetaTag
from .middleware import Seo


@receiver(post_save, sender=RobotsTxt)
def robots_txt_changed(sender, instance, **kwargs):
    """
    When changing the contents of any robots.txt, its cache is updated.
    """
    cache_key = f'{ROBOT_TXT_CACHE_KEY_PREFIX}:{instance.pk}'
    cache.set(cache_key, get_robots_txt_content(instance.pk))


@receiver(post_delete, sender=MetaTag)
@receiver(post_save, sender=MetaTag)
def metatag_saved_or_deleted(sender, instance, **kwargs):
    """
    Invalidation of cache when adding, changing, or deleting a MetaTag object.
    """
    cache.set(Seo.CACHE_KEY, MetaTag.objects.all(), 60 * 60 * 60)
