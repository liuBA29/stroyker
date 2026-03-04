from django.http import HttpResponse
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache

from .models import RobotsTxt

ROBOT_TXT_CACHE_KEY_PREFIX = 'robots_txt'


def get_robots_txt_content(site_id):
    try:
        return RobotsTxt.objects.get(pk=site_id).content
    except RobotsTxt.DoesNotExist:
        return ''


def robots_txt(request):
    site_id = get_current_site(request).id
    cache_key = f'{ROBOT_TXT_CACHE_KEY_PREFIX}:{site_id}'
    content = cache.get_or_set(cache_key, get_robots_txt_content(site_id))

    return HttpResponse(content, content_type='text/plain')
