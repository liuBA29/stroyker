from django.dispatch import receiver
from django.db.models.signals import post_save
from django.db import transaction
from django.core.cache import cache

from constance import config

from .tasks import search_index_updater
from .models import Page, PageContructor


@receiver(post_save, sender=Page)
def staticpage_saved(sender, instance, **kwargs):
    if all((
        instance.published,
        config.SEARCH__USE_FULLTEXT,
    )):
        transaction.on_commit(
            lambda: search_index_updater.delay(instance))


@receiver(post_save, sender=PageContructor)
def clear_page_constructor_cache(sender, instance, **kwargs):
    if instance.cache:
        cache.delete(instance.cache_key)
