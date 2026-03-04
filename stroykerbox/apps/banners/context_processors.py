from stroykerbox.apps.banners.utils import get_banners_for_url


def banners(request):
    return {'page_banners': list(get_banners_for_url(request.path))}
