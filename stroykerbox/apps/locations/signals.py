from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from .models import Location


@receiver(pre_save, sender=Location)
def pre_save_location(sender, instance, **kwargs):
    qs = sender.objects.all()
    if instance.is_default:
        # There can be only one default location.
        qs.filter(is_default=True).update(is_default=False)
    elif instance.is_active and (
            not qs.filter(is_active=True).exclude(pk=instance.pk).exists()):
        # A single location should also be the default location.
        instance.is_default = True


@receiver(post_delete, sender=Location)
@receiver(post_save, sender=Location)
def clear_locations_cache(sender, instance, **kwargs):
    """
    Cache update when changing or deleted any location object.
    """
    locations = Location.objects.filter(is_active=True).order_by('city__name')
    cache.set(Location._available_locations_cache_key(), locations)

    cache_key = Location._default_location_cache_key()
    try:
        default_location = Location.objects.get(is_default=True, is_active=True)
        cache.set(cache_key, default_location)
    except Location.DoesNotExist:
        cache.delete(cache_key)
