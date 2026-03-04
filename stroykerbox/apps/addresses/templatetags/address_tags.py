from django import template

from constance import config
from stroykerbox.apps.addresses.models import Partner
from stroykerbox.apps.locations.models import Location


register = template.Library()


@register.inclusion_tag(
    'addresses/tags/frontpage-partner-promo-block.html', takes_context=True
)
def render_frontpage_partner_promo_block(context):
    qs = Partner.objects.filter(is_active=True)
    context['partners_count_total'] = qs.count()
    current_location = getattr(context['request'], 'location')
    if current_location:
        context['partners_count_region'] = qs.filter(location=current_location).count()
    return context


@register.inclusion_tag('addresses/tags/partners-yamap.html', takes_context=True)
def render_partners_yamap(context, use_main_store_address=False):
    qs = Partner.objects.filter(is_active=True)
    request = context.get('request', None)
    location = getattr(request, 'location') or Location.get_default_location()

    # Для блока «Где мы находимся» на странице 8 марта — просто карта Самары, район метро Московская
    if use_main_store_address:
        context['use_main_store_address'] = True
        # Район метро Московская, Самара (без кастомного маркера — только карта)
        context['center_latitude'] = 53.215
        context['center_longitude'] = 50.150
        context['center_zoom'] = 15
        # не задаём main_store_latitude/longitude — маркер не выводим
    else:
        context['use_main_store_address'] = False
        context['center_latitude'] = (
            location.latitude if location else config.YAMAP_DEFAULT_CENTER_LATITUDE
        )
        context['center_longitude'] = (
            location.longitude if location else config.YAMAP_DEFAULT_CENTER_LONGITUDE
        )
        context['center_zoom'] = config.YAMAP_DEFAULT_CENTER_ZOOM

    filter = {}
    if location and not use_main_store_address:
        filter['location_id'] = location.id
    else:
        filter['location__isnull'] = True

    partners = qs.filter(**filter)

    context['use_glyph'] = partners.filter(ymap_glyph_icon__isnull=False).exists()
    context['partners'] = partners

    return context
