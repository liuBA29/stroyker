from django import template

from constance import config
from stroykerbox.apps.banners.models import BannerSet, BannerMultirowSet, BannerMultirowSetRows
from stroykerbox.apps.banners.utils import get_banners_for_url, check_page_has_banners


register = template.Library()

CATALOG_BANNERS_KEY = 'catalog_page_banners'


def update_context_with_banners(context, limit=None):
    url = getattr(context.get('request', None), 'path', None)
    page_banners = (context['page_banners'] if 'page_banners' in
                    context else list(get_banners_for_url(url)))
    context['banners'] = None
    if page_banners:
        context['banners'] = [page_banners.pop(0)
                              for b in page_banners[:limit] if b]
        context['page_banners'] = page_banners
    return context


def update_context_for_catalog_page_banners(context):
    """
    Formation of banners for the sidebar and content area on
    the parent catalog category page. For the White Theme only.
    """

    if CATALOG_BANNERS_KEY not in context:
        banners_dict = {}
        url = getattr(context.get('request', None), 'path', None)
        page_banners = list(get_banners_for_url(url))

        def banner_slice(limit=None):
            return [page_banners.pop(0) for b in page_banners[:limit] if b]

        sidebar_first = config.WHITETHEME_BANNERS_FOR_CATALOG_SIDEBAR_FIRST
        if sidebar_first:
            limit = config.WHITETHEME_BANNERS_FOR_CATALOG_SIDEBAR_FIRST_LIMIT
            banners_dict['sidebar'] = banner_slice(limit)
            banners_dict['content'] = page_banners
        else:
            limit = config.WHITETHEME_BANNERS_FOR_CATALOG_CONTENT_FIRST_LIMIT
            banners_dict['content'] = banner_slice(limit)
            banners_dict['sidebar'] = page_banners

        context[CATALOG_BANNERS_KEY] = banners_dict

    return context


@register.inclusion_tag('banners/tags/banners-horizontal.html', takes_context=True)
def render_catalog_page_banners_horizontal(context, title=None):
    context = update_context_for_catalog_page_banners(context)

    page_banners = context.get(CATALOG_BANNERS_KEY)
    if isinstance(page_banners, dict):
        context['banners'] = page_banners.get('content')
        context['title'] = title

    return context


@register.inclusion_tag('banners/tags/banners-sidebar.html', takes_context=True)
def render_catalog_page_sidebar_banners(context):
    context = update_context_for_catalog_page_banners(context)

    page_banners = context.get(CATALOG_BANNERS_KEY)
    if isinstance(page_banners, dict):
        context['banners'] = page_banners.get('sidebar')
    return context


@register.inclusion_tag('banners/tags/banners-sidebar.html', takes_context=True)
def render_sidebar_banners(context, limit=None):
    return update_context_with_banners(context, limit)


@register.inclusion_tag('banners/tags/banners.html', takes_context=True)
def render_banners(context, limit=None):
    return update_context_with_banners(context, limit)


@register.inclusion_tag('banners/tags/banners-horizontal.html', takes_context=True)
def render_banners_horizontal(context, limit=None):
    return update_context_with_banners(context, limit)


@register.filter
def has_banners(path):
    """
    Check that there are banners for the current page.
    """
    return check_page_has_banners(path)


@register.inclusion_tag('banners/tags/banner-set.html', takes_context=True)
def render_banner_set(context, key):
    bannerset_qs = BannerSet.objects.prefetch_related(
        'bannerset_items').filter(key=key, published=True).first()
    context['bannerset'] = bannerset_qs
    return context


@register.inclusion_tag('banners/tags/banner-multirow-set.html', takes_context=True)
def render_multirow_banner_set(context, key):
    try:
        bannerset = BannerMultirowSet.objects.get(key=key)
    except BannerMultirowSet.DoesNotExist:
        return {}

    context.update({
        'rowsets': BannerMultirowSetRows.objects.filter(multirowset__key=key),
        'banners_per_line': bannerset.banners_per_line
    })
    return context
