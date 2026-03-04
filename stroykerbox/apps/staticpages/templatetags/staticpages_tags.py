import os

from django import template
from django.conf import settings
from django.utils.html import mark_safe

from stroykerbox.apps.staticpages.models import get_page_url

register = template.Library()


@register.simple_tag
def get_staticpage_url(key):
    return get_page_url(key)


@register.filter
def icon(item):
    if item['icon']:
        path = os.path.join(settings.BASE_DIR, 'media', item['icon'])
        return mark_safe(open(path, mode='r').read())
