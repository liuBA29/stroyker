from django.core.cache import cache

from stroykerbox.apps.banners import BANNERS_FOR_URL_CACHE_PREFIX
from stroykerbox.apps.banners.models import Banner, StroykerBanner


def shuffle_banners(client_banners, stroyker_banners):
    banners = [client_banners.pop(0), stroyker_banners.pop(0)]
    if client_banners:
        banners.append(client_banners.pop(0))
    if stroyker_banners:
        banners.append(stroyker_banners.pop(0))

    return banners + client_banners + stroyker_banners


def get_banners_for_url(url):
    cache_key = f'{BANNERS_FOR_URL_CACHE_PREFIX}:{url}'
    banners = cache.get(cache_key)
    if not banners:
        client_banners = Banner.objects.get_active_for_url(url)
        stroyker_banners = StroykerBanner.objects.get_active_for_url(url)
        if not stroyker_banners:
            banners = client_banners
        elif client_banners:
            banners = shuffle_banners(
                list(client_banners), list(stroyker_banners))
        else:
            banners = stroyker_banners
        cache.set(cache_key, banners, 3600)

    return banners


def check_page_has_banners(url):
    """
    Checking that the page has banners.
    """
    return (Banner.objects.get_active_for_url(url).exists() or
            StroykerBanner.objects.get_active_for_url(url).exists())
