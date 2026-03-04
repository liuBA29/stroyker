from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import SearchWordAlias


@receiver(post_save, sender=SearchWordAlias)
def rebuild_aliases_cache(sender, *args, **kwargs):
    SearchWordAlias.create_search_aliases_cache()
