from django import template

from stroykerbox.apps.locations.models import Location
from stroykerbox.apps.utils.utils import get_site_phones


register = template.Library()


def get_location_block_context(current_context):
    locations = Location.get_available_locations()
    if locations.count() > 1:
        current_location = getattr(
            current_context['request'], 'location', None) or locations.filter(is_default=True).first()
        return {
            'current_location': current_location,
            'locations': locations
        }
    return {}


@register.inclusion_tag('locations/tags/current-location-block.html', takes_context=True)
def render_current_location_block(context, mobile_mode=False):
    tpl_context = get_location_block_context(context)
    tpl_context['mobile_mode'] = mobile_mode
    return tpl_context


@register.inclusion_tag('locations/tags/custom-header-location-block.html', takes_context=True)
def render_custom_header_location_block(context, mobile_mode=False, link_class='location-caret', show_arrow=None):
    tpl_context = get_location_block_context(context)
    tpl_context['mobile_mode'] = mobile_mode
    tpl_context['link_class'] = link_class
    tpl_context['show_arrow'] = show_arrow
    return tpl_context


@register.simple_tag(takes_context=True)
def location_contact_phone(context):
    location = context['request'].location
    phones = get_site_phones(location)
    if phones:
        return phones[0]
    return []


@register.simple_tag(takes_context=True)
def location_contact_phones(context):
    location = context['request'].location or Location.get_default_location()
    phones = get_site_phones(location)

    return phones
