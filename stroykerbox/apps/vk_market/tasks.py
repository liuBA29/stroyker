from logging import getLogger
from datetime import timedelta

from django.utils import timezone
from django.core.cache import cache
from django.core.management import call_command
from django_rq import job
from constance import config
from django.conf import settings


from .vk import vk_market_enabled


logger = getLogger(__name__)


VK_SYNC_CACHE_KEY = 'vk_market_last_sync'


@job
def vk_market_process_product(product_id):
    call_command('vk_sync', product_id, verbosity=0)


@job('default', timeout=43200)
def vk_market_sync():
    if (not vk_market_enabled() or not
        config.VK_MAKET_SYNC_PERIOD or
            config.VK_MAKET_SYNC_PERIOD == '0'):
        return

    last_sync = cache.get(VK_SYNC_CACHE_KEY)
    now = timezone.now()

    if last_sync:
        if last_sync + timedelta(seconds=config.VK_MAKET_SYNC_PERIOD) > now:
            return
    else:
        cache.set(VK_SYNC_CACHE_KEY, now, config.VK_MAKET_SYNC_PERIOD)

    call_command('vk_sync', verbosity=0)


@job('default', timeout=43200)
def run_vk_sync_manually():
    if 'stroykerbox.apps.vk_market' in settings.INSTALLED_APPS and vk_market_enabled():
        now = timezone.now()
        cache.set(VK_SYNC_CACHE_KEY, now, config.VK_MAKET_SYNC_PERIOD)
        return call_command('vk_sync')
