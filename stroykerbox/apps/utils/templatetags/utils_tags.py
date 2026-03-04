import calendar
import re
from datetime import date

from django.utils.translation import ugettext as _
from django import template
from django.http import QueryDict
from django.conf import settings
from django.utils.safestring import mark_safe

from constance import config

from stroykerbox import __version__
from stroykerbox.apps.utils.forms import StockFilterForm
from stroykerbox.apps.utils.utils import (
    get_site_phones,
    clear_phone as clear_phone_util,
)
from stroykerbox.apps.catalog.models import Category
from stroykerbox.apps.menu.models import Menu
from stroykerbox.apps.commerce.cart import Cart
from stroykerbox.apps.locations.models import Location

register = template.Library()


@register.simple_tag(takes_context=True)
def url_with_querystring(context, append=True, _packed=None, **kwargs):
    if append:
        qd = context['request'].GET.copy()
    else:
        qd = QueryDict('', mutable=True)
    # merge _packed into kwargs
    if _packed is not None:
        assert isinstance(_packed, QueryDict)
        _packed = _packed.copy()
        for k, v in kwargs.items():
            _packed.setlist(k, [v])
        kwargs = _packed
    # merge kwargs into QueryDict
    for k, v in kwargs.items():
        if v is not None:
            if isinstance(kwargs, QueryDict):
                qd.setlist(k, kwargs.getlist(k))
            else:
                qd.setlist(k, [v])
        else:
            # remove keys with None values
            try:
                qd.pop(k)
            except KeyError:
                pass
    querystring = qd.urlencode()
    if querystring:
        return context['request'].path + '?' + querystring
    else:
        return context['request'].path


@register.filter
def math_abs(n):
    return abs(n)


@register.filter
def sub(n1, n2):
    return n1 - n2


@register.filter
def keep_tags(value, tags):
    """
    Strips all [X]HTML tags except the given tags
    """
    tags = [re.escape(tag) for tag in tags]
    tags_re = re.compile(
        r'<[^{tags}]+>'.format(tags='|'.join(tags)), re.IGNORECASE | re.DOTALL
    )
    return re.sub(tags_re, '', value)


style_re = re.compile(r''' ?style=".*?"''', re.DOTALL)


@register.filter
def remove_styles(value):
    """
    Strips all style attributes from all HTML tags.
    """
    return re.sub(style_re, '', value)


@register.filter
def klass(value):
    """
    Get a class name of the instance as a string.
    """
    return value.__class__.__name__


@register.simple_tag
def settings_value(name):
    return getattr(settings, name, '')


@register.simple_tag
def config_value(name, safe=False):
    result = getattr(config, name, '')
    if safe and result:
        return mark_safe(result)
    return result


@register.filter
def split_by_newline(string):
    return '</br>'.join(string.split(' '))


@register.filter
def str_to_date(value, format):
    date_value = value.split()[0]
    try:
        result = date.fromisoformat(date_value).strftime(format)
    except ValueError:
        result = value
    return result


@register.filter()
def multiplication(a, b):
    return a * b


@register.filter
def month_name(month_number):
    return _(calendar.month_name[month_number])


@register.filter()
def fieldtype(field):
    return field.field.widget.__class__.__name__


@register.filter()
def file_size(file):
    """
    This will return the file size converted
    from bytes to MB... GB... etc
    """
    file_size = file.size

    if file_size < 512000:
        file_size /= 1024.0
        ext = _('Kb')
    elif file_size < 4194304000:
        file_size /= 1048576.0
        ext = _('Mb')
    else:
        file_size /= 1073741824.0
        ext = _('Gb')
    return '%s %s' % (str(round(file_size, 1)), ext)


@register.filter()
def file_extension(file):
    from pathlib import Path

    return Path(file.url).suffix[1:4]


@register.filter()
def rub2words(num):
    """
    Convert rubles num to words.
    (42.00 --> Сорок два рубля, ноль копеек)
    """
    try:
        from num2words import num2words
    except ImportError:
        return ''

    return num2words(num, lang='ru', to='currency', currency="RUB")


@register.inclusion_tag('utils/tags/footer-social-links.html')
def render_footer_social_links():
    if config.SOCIAL_LINKS_ENABLED:
        return {'config': config}


@register.simple_tag()
def utils_yandex_metrika_code():
    return mark_safe(config.YANDEX_METRIKA_CODE) or ''


@register.filter(name='hex_to_rgb')
def hex_to_rgb(hex, format_string='rgb({r},{g},{b})'):
    """
    Returns the RGB value of a hexadecimal color
    """
    hex = hex.replace('#', '')
    out = {'r': int(hex[0:2], 16), 'g': int(hex[2:4], 16), 'b': int(hex[4:6], 16)}
    return format_string.format(**out)


@register.filter
def index(indexable, i):
    return indexable[i]


@register.inclusion_tag('utils/tags/header-contact-phone.html', takes_context=True)
def render_header_contact_phone(context, phone_per_box=2):
    if (
        config.HIDE_PHONE_IN_HEADER
        and config.YANDEX_METRICA_COUNTER_ID
        and config.YANDEX_METRICA_PHONE_TARGET_NAME
    ):
        context['is_hidden'] = True
    location = context['request'].location
    phones = get_site_phones(location)

    if len(phones) > phone_per_box:
        context['phone_boxes'] = [phones[:phone_per_box], phones[phone_per_box:]]
    else:
        context['phone_boxes'] = [phones]

    if getattr(location, 'email', None) and config.LOCATION_EMAIL_SHOW_IN_HEADER:
        context['location_email'] = location.email
    return context


@register.inclusion_tag('utils/tags/custom-header-phone.html', takes_context=True)
def render_custom_header_phone(context, mobile_mode=False):
    if (
        config.HIDE_PHONE_IN_HEADER
        and config.YANDEX_METRICA_COUNTER_ID
        and config.YANDEX_METRICA_PHONE_TARGET_NAME
    ):
        context['is_hidden'] = True
    location = context['request'].location

    context['phones'] = get_site_phones(location)
    context['mobile_mode'] = mobile_mode

    if getattr(location, 'email', None) and config.LOCATION_EMAIL_SHOW_IN_HEADER:
        context['location_email'] = location.email

    return context


@register.simple_tag()
def render_yandex_metrika_goal(target_name):
    if all(
        (
            target_name,
            config.YANDEX_METRICA_COUNTER_ID,
            config.YANDEX_METRICA_COUNTER_ID > 0,
        )
    ):
        return f"ym({config.YANDEX_METRICA_COUNTER_ID}, 'reachGoal', '{target_name}'); return true;"
    return ''


@register.simple_tag()
def project_version():
    if __version__:
        return f'v.{__version__}'


@register.filter
def startswith(text, starts):
    if isinstance(text, str):
        return text.startswith(starts)
    return False


@register.filter(name='getattr')
def getattribute(obj, attr):
    return getattr(obj, attr, '')


@register.filter
def getbydictkey(dict_obj, key):
    if not isinstance(dict_obj, dict):
        return
    return dict_obj.get(key)


@register.inclusion_tag(
    'utils/tags/search-by-stock-sidebar-filter.html', takes_context=True
)
def render_search_by_stock_filter(context, products=None):
    initial = {'stock': context.request.GET.getlist('stock')}
    context['form'] = StockFilterForm(products=products, initial=initial)
    return context


@register.inclusion_tag('utils/tags/recaptcha-terms.html')
def render_recaptcha_terms_text():

    context = {}

    captcha_enabled = all(
        (
            config.CAPTCHA_MODE == 'google',
            config.RECAPTCHA_PRIVATE_KEY,
            config.RECAPTCHA_PUBLIC_KEY,
        )
    ) and any(
        (
            config.RECAPTCHA_REGISTRATION_FORM,
            config.RECAPTCHA_FEEDBACK_FORM,
            config.RECAPTCHA_CALLME_FORM,
            config.RECAPTCHA_CART_FORM,
            config.RECAPTCHA_CUSTOM_FORMS,
            config.CAPTCHA_USE_FOR_BOOKING_FORM,
        )
    )
    if captcha_enabled:
        context['recaptcha_terms'] = _(
            'This site is protected by reCAPTCHA and the Google'
            '<a href="https://policies.google.com/privacy"> Privacy Policy </a> and'
            '<a href="https://policies.google.com/terms"> Terms of Service </a> apply.'
        )

    return context


@register.inclusion_tag('utils/tags/mmenujs.html', takes_context=True)
def render_mmenujs(context, **kwargs):
    context['mmenu_categories'] = Category.objects.filter(published=True)
    location = (
        getattr(context['request'], 'location', None) or Location.get_default_location()
    )

    # костыли для нового моб. меню v3-new
    if 'header_menu' not in context:
        header_menu_key = kwargs.get('header_menu_key', 'header_menu')
        header_menu_limit = kwargs.get('header_menu_limit', None)
        try:
            menu = Menu.objects.get(key=header_menu_key)
            context['header_menu'] = menu.get_published_items[:header_menu_limit]
        except Menu.DoesNotExist:
            context['header_menu'] = []
    if 'cart' not in context:
        context['cart'] = context.get('cart', Cart.from_request(context['request']))
    if 'phones' not in context:
        context['phones'] = get_site_phones(location)

    # отображаем локации в mmenu, только если их больше 1-й
    active_locations = Location.objects.filter(is_active=True)
    context['show_locations'] = active_locations.count() > 1
    context['active_locations'] = active_locations
    context['current_location'] = location

    return context


@register.filter
def clear_phone(input_phone, country_code=7):
    return clear_phone_util(input_phone, country_code=country_code)


@register.inclusion_tag('utils/tags/footer-playmarket.html')
def render_footer_playmarket():
    return {'config': config}


@register.filter
def islist(value):
    return isinstance(value, (list, tuple))


@register.inclusion_tag('utils/tags/lang-switcher.html', takes_context=True)
def render_lang_switcher(context):
    return context


@register.filter
def list_sort(value, reverse=False):
    if isinstance(value, (list, tuple)) and hasattr(value, 'sort'):
        value.sort(reverse=reverse)
    return value


@register.filter
def has_attr(value, attr: str) -> bool:
    try:
        return bool(getattr(value, attr, None))
    except ValueError:
        return False
