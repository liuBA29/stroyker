import random
from decimal import Decimal, InvalidOperation
from typing import Sequence, Optional, Any
from collections import defaultdict

from django.db.models import QuerySet
from django import template
from django.db.models import Q
from django.utils.translation import ugettext as _
from django.utils.html import mark_safe
from django.contrib.sites.models import Site

from constance import config
from stroykerbox.apps.catalog.models import (
    Category,
    Product,
    ProductSet,
    ProductSetMembership,
    ProductRelated,
)

from stroykerbox.apps.catalog import RECENTLY_WATCHED_SESS_KEY
from stroykerbox.apps.catalog.utils import get_formatted_price
from stroykerbox.apps.commerce.cart import Cart


register = template.Library()


def get_context_location(context: dict[str, Any]):
    if 'location' in context:
        return context['location']

    return getattr(context.get('request'), 'location', None)


def get_published_categories(level: Optional[int] = None) -> QuerySet:
    categories = Category.objects.filter(published=True)
    if level is not None:
        categories = categories.filter(level=level)
    return categories


@register.inclusion_tag('catalog/tags/categories-menu.html', takes_context=True)
def render_category_siblings(context, category):
    if category.parent:
        context['categories'] = Category.objects.filter(
            parent_id=category.parent_id, published=True
        ).exclude(id=category.id)
    context['template'] = 'catalog/tags/categories-menu-base.html'
    return context


@register.inclusion_tag('catalog/tags/categories-menu.html', takes_context=True)
def render_catalog_categories_menu(context, category=None):
    categories = get_published_categories(0)
    template = 'catalog/tags/categories-menu-base.html'
    request = context.get('request')
    current_path_is_front = bool(getattr(request, 'path', None) == '/')

    if category and category.parent:
        categories = categories.filter(parent_id=category.parent_id).exclude(
            id=category.id
        )

    if current_path_is_front:
        context['show_more'] = True
        if config.CATALOG_MENU_ITEMS_LIMIT > 0:
            categories = categories[: config.CATALOG_MENU_ITEMS_LIMIT]
    elif (
        config.CATALOG_SHOW_CHILDS_IN_PARENT
        or config.CATALOG_PRODUCT_LIST_ON_INDEX_PAGE
    ):
        template = 'catalog/tags/categories-menu-catalog-page.html'

    context['categories'] = categories
    context['template'] = template
    return context


@register.inclusion_tag('catalog/tags/categories-menu-mobile.html', takes_context=True)
def render_catalog_categories_menu_mobile(context, simple=True):
    context.update({'categories': get_published_categories(0), 'simple': simple})
    return context


@register.inclusion_tag('catalog/tags/catalog-menu-mobile-new.html', takes_context=True)
def render_catalog_menu_mobile_new(context):
    context['categories'] = get_published_categories(0)
    return context


@register.inclusion_tag(
    'catalog/tags/catalog-custom-header-mobile.html', takes_context=True
)
def render_catalog_custom_header_mobile(context, level=None):
    context['categories'] = get_published_categories(level)
    return context


@register.inclusion_tag('catalog/tags/categories-menu-simple.html', takes_context=True)
def render_catalog_categories_menu_simple(context, max_rows=None):
    categories = get_published_categories(0)
    context['categories'] = categories
    if max_rows and isinstance(max_rows, int) and max_rows < categories.count():
        context['max_rows'] = max_rows
    return context


@register.simple_tag(takes_context=True)
def url_add_qs(context, field, value):
    '''
    Возвращаем querystring для запрошенного пути.
    Если таковой имеется, конечно.
    '''
    d = context['request'].GET.copy()
    d[field] = value
    return d.urlencode()


@register.simple_tag(takes_context=True)
def url_qs_array(context, field, value, remove=False):
    '''
    Добавляем в массив (или удаляем из массива) для конкретного поля в querystring для запрошенного пути.
    '''
    d = context['request'].GET.copy()
    lst = context['request'].GET.getlist(field)

    if remove:
        try:
            lst.remove(value)
        except ValueError:
            pass
    elif value not in lst:
        lst.append(value)

    d.setlist(field, lst)
    return d.urlencode()


@register.inclusion_tag(
    'catalog/tags/product-availability-status.html', takes_context=True
)
def render_product_availability_status(context, detail_mode=False, product_object=None):
    """
    https://redmine.fancymedia.ru/issues/11436
    """
    request = context['request']
    status = days_to_arrive = None
    product = product_object or context.get('product')
    location = get_context_location(context)
    count = 0

    if product:
        count = product.available_items_count(location)

        # ('1', 'показывать заглушку'),
        if count > 0 and config.PRODUCT_AVAIL_LABEL_VARIANT != '1':
            if detail_mode and config.PRODUCT_SHOW_AVAIL_STOCKS:
                context['stocks'] = product.availability_by_stocks(location)

            if config.PRODUCT_AVAIL_LABEL_VARIANT == '2' or (
                config.PRODUCT_AVAIL_LABEL_VARIANT == '3' and request.user.is_anonymous
            ):
                # ('2', 'показывать диапазон всем'),
                # ('3', 'показывать диапазон неавторизованным, авторизованным кол-во'),
                status = product.get_availability_status_name(location)
            else:
                # ('4', 'показывать кол-во всем'),
                status = count

        else:
            if product.days_to_arrive:
                days_to_arrive = product.days_to_arrive

    context['count'] = count
    context['status'] = status
    context['days_to_arrive'] = days_to_arrive

    return context


@register.simple_tag(takes_context=True)
def render_product_availability_status_text(context, product):
    location = get_context_location(context)

    if product.available_items_count(location) > 0:
        return product.get_availability_status_name(location)
    return config.PRODUCT_NOT_AVAIBLE_STATUS_NAME


@register.inclusion_tag('catalog/tags/cart-related-products.html', takes_context=True)
def render_cart_related_products(context, cart_products=None):
    related_products = (
        Product.objects.filter(related__ref__in=cart_products, published=True)
        .exclude(product__in=cart_products)
        .exclude_by_modification_code()
    )
    context['related_products'] = {
        item.product
        for item in related_products
        if item.product.available_items_count(context.get('request').location)
    }
    return context


@register.inclusion_tag('catalog/tags/product-teaser.html', takes_context=True)
def render_catalog_product_teaser(context, product):
    context['product'] = product
    return context


@register.simple_tag(takes_context=True)
def personal_price(context, product):
    """
    Proxy to Product.personal_price()
    """
    request = context.get('request')
    if request:
        return product.personal_price(request.user, request.location)


@register.simple_tag(takes_context=True)
def product_location_price(context, product):
    location = get_context_location(context)
    return getattr(product.location_price_object(location), 'currency_price', None)


@register.simple_tag(takes_context=True)
def product_online_price(context, product):
    location = get_context_location(context)
    user = getattr(context.get('request'), 'user')
    return product.online_price(user, location)


@register.simple_tag(takes_context=True)
def product_location_old_price(context, product):
    location = get_context_location(context)
    return getattr(product.location_price_object(location), 'currency_old_price', None)


@register.simple_tag(takes_context=True)
def product_location_purchase_price(context, product):
    location = context.get('request').location
    return getattr(
        product.location_price_object(location), 'currency_purchase_price', None
    )


@register.inclusion_tag(
    'catalog/tags/bestseller-products-slider.html', takes_context=True
)
def render_bestsellers_slider(context, num=12):
    bestseller_products = (
        Product.objects.published().exclude_by_modification_code().filter(is_hit=True)
    )
    count = bestseller_products.count()
    if count < num:
        num = count // 2 * 2
    location = context.get('request').location
    if location:
        bestseller_products = [
            p for p in bestseller_products if p.is_available(location)
        ]
    context['products'] = bestseller_products[:num]
    return context


@register.inclusion_tag('catalog/tags/sale-products-slider.html', takes_context=True)
def render_sales_slider(context, num=12):
    sale_products = (
        Product.objects.published().filter(is_sale=True).exclude_by_modification_code()
    )
    if not config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE:
        sale_products = sale_products.filter(stocks_availability__available__gt=0)
    location = context.get('request').location
    if location:
        sale_products = [p for p in sale_products if p.is_available(location)]
    context['products'] = sale_products[:num]
    return context


@register.inclusion_tag('catalog/tags/new_spring_design_sale-products-slider.html', takes_context=True)
def render_new_spring_design_sales_slider(context, num=12):
    """
    Слайдер товаров по акции в стиле «новый весенний дизайн» (8 марта).
    Показ в случайном порядке для разнообразия. Все акционные товары без ограничения по количеству.
    """
    sale_products = (
        Product.objects.published().filter(is_sale=True).exclude_by_modification_code()
    )
    if not config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE:
        sale_products = sale_products.filter(stocks_availability__available__gt=0)
    location = get_context_location(context)
    if location:
        sale_products = [p for p in sale_products if p.is_available(location)]
        random.shuffle(sale_products)
        context['products'] = sale_products
    else:
        context['products'] = list(sale_products.order_by('?'))
    return context


@register.inclusion_tag('catalog/tags/product-images-slider.html', takes_context=True)
def render_product_images_slider(context):
    product = context.get('product')
    if product:
        context['images'] = product.images.all()
    return context


@register.inclusion_tag('catalog/tags/product-flags.html', takes_context=True)
def render_product_flags(context):
    context['product'] = context.get('product', None)
    return context


@register.inclusion_tag('catalog/tags/product-flags-v2.html', takes_context=True)
def render_product_flags_v2(context):
    context['product'] = context.get('product', None)
    return context


@register.inclusion_tag('catalog/tags/product-price-chart.html', takes_context=True)
def render_product_price_chart(context):
    context['chart_data'] = context.get('chart_data', None)
    return context


@register.inclusion_tag('catalog/tags/product-documents.html', takes_context=True)
def render_product_documents(context):
    context['product'] = context.get('product', None)
    return context


@register.filter
def is_available(product, location):
    return product.is_available(location)


@register.simple_tag(takes_context=True)
def product_available_qty(context):
    """
    Available quantity of the product.
    """
    product = context.get('product')
    location = get_context_location(context)
    if product:
        return product.available_items_count(location)
    return 0


@register.inclusion_tag('catalog/tags/products-list-header.html', takes_context=True)
def render_products_list_header(context, line_display_mode=True):
    context['line_display_mode'] = line_display_mode
    return context


@register.inclusion_tag('catalog/tags/catalog-filter.html', takes_context=True)
def render_catalog_filter(context):
    return context


@register.inclusion_tag('catalog/tags/product-properties.html', takes_context=True)
def render_product_properties(context):
    product = context.get('product', None)

    def filter_delivery_props(delivery_prop: Sequence) -> bool:
        if delivery_prop[1]:
            return True
        return False

    filtered_delivery_props = filter(
        filter_delivery_props,
        [
            (_('Weight, kg'), product.weight),
            (_('Volume, m3'), product.volume),
            (_('Lenght, mm'), product.length),
            (_('Width, mm'), product.width),
            (_('Height, mm'), product.height),
        ],
    )

    if product:
        context['delivery_props'] = list(filtered_delivery_props)
    else:
        context['delivery_props'] = []
    context['product'] = product
    return context


@register.inclusion_tag('catalog/tags/product-set-base.html', takes_context=True)
def render_product_set_slider(context, key, rows=None):
    from django.db.models import Prefetch
    from stroykerbox.apps.catalog.context_processors import catalog_context

    request = context.get('request')

    # Из-за конфликов хаков-костылей для функционала "кастомных блоков" c кодом шаблонизатора Django
    # при рендере кода внутрь этих "кастомных блоков" периодически не доходит глобальный контекст с нужными для
    # шаблона переменными.
    # Решения лучше, чем еще один костыль с принудительным дублированием глобальных переменных контекста Каталога,
    # на данный момент не найдено.
    if request:
        context.update(catalog_context(request))

    if key:
        try:
            product_set = ProductSet.objects.prefetch_related(
                Prefetch(
                    'products',
                    queryset=ProductSetMembership.objects.select_related(
                        'product', 'product__uom'
                    )
                    .filter(published=True, product__published=True)
                    .prefetch_related('product__images'),
                )
            ).get(key=key)
        except ProductSet.DoesNotExist:
            return context

        context['product_set'] = product_set
        context['items'] = product_set.products.all()
        context['title'] = context.get('custom_block_title', product_set.title)
        context['rows'] = rows or product_set.rows
        context['banners'] = []

        page_banners = context.get('page_banners')

        # disable built-in banners for new teaser variants also
        if product_set.banners and page_banners:
            for __ in range(product_set.rows):
                try:
                    context['banners'].append(page_banners.pop(0))
                except IndexError:
                    break
    return context


@register.inclusion_tag('catalog/tags/categories-list-popular.html', takes_context=True)
def render_catalog_categories_list_popular(context):
    context['categories'] = get_published_categories(0)
    return context


@register.inclusion_tag('catalog/tags/product-comparision.html', takes_context=True)
def product_comparision(context, simple=False):
    product = context.get('product', False)
    if product:
        action_comparision = (
            'del'
            if product.pk in (context['request'].session.get('comparision') or [])
            else 'add'
        )
        return {
            'action_comparision': action_comparision,
            'product': product,
            'simple': simple,
        }


@register.inclusion_tag('catalog/tags/comparison-link.html', takes_context=True)
def comparison_link(context):
    context['count_comparision_products'] = len(
        context['request'].session.get('comparision') or []
    )
    return context


@register.filter
def canonical_link(url):
    """Return canonical absolute link"""
    domain = Site.objects.get_current().domain
    return 'http://{}{}'.format(domain, url)


@register.filter
def price_format(price, use_intcomma=True):
    """
    Return with or without pennies, depending on the current settings.
    """
    return get_formatted_price(price, use_intcomma)


@register.filter
def price_with_space(value):
    """Формат цены с пробелом между разрядами (2 000), как в блоке «Сборные букеты»."""
    if value is None or value == '':
        return ''
    try:
        amount = Decimal(str(value)).quantize(Decimal('1'))
    except (InvalidOperation, TypeError, ValueError):
        return ''
    return f"{int(amount):,}".replace(',', ' ')




@register.inclusion_tag('catalog/tags/root-categories-slider.html', takes_context=True)
def render_root_category_slider(context):
    context['categories'] = get_published_categories(0)
    return context


@register.inclusion_tag(
    'catalog/tags/root-category-top-products.html', takes_context=True
)
def render_root_category_top_products(context, categories_list, limit=8):
    qs = (
        Product.objects.published()
        .exclude_by_modification_code()
        .filter(categories__in=categories_list, is_hit=True)
    )
    if not config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE:
        qs = qs.filter(stocks_availability__available__gt=0)
    context['products'] = qs[:limit]
    return context


@register.inclusion_tag('catalog/tags/category-image.html', takes_context=True)
def render_category_image(context, category, demensions='250x200'):
    context.update({'obj': category, 'demensions': demensions})
    if demensions:
        width, height = demensions.split('x')
        context['img_width'] = width
        context['img_height'] = height
    return context


@register.inclusion_tag(
    'catalog/tags/category-maybeinteresterd-block.html', takes_context=True
)
def render_category_maybeinterested_block(context, category, limit=8):
    related_categories = set(category.related_categories.all())
    all_products_qs = (
        Product.objects.published()
        .filter(categories__in=related_categories)
        .exclude_by_modification_code()
        .prefetch_related('categories')
        .order_by('?')
    )

    if not config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE:
        all_products_qs = all_products_qs.filter(stocks_availability__available__gt=0)

    categories = defaultdict(list)
    for product in all_products_qs:
        for category in product.categories.all():
            if category in related_categories:
                categories[category].append(product)
    result = []
    while len(result) < limit:
        for category, products in list(categories.items()):
            if products:
                result.append(products.pop(0))
            else:
                del categories[category]
            if len(result) == limit:
                break
        if not categories:
            break

    context['maybeinterested_products'] = result
    return context


@register.inclusion_tag('catalog/tags/product-card-v2.html', takes_context=True)
def render_product_teaser(context, product):
    return context


@register.inclusion_tag('catalog/tags/product-list-slider-v2.html', takes_context=True)
def render_product_list_slider(context, products, **kwargs):
    """
    White theme only.
    """
    context.update(
        {
            'products': products,
            'cols': kwargs.get('cols', 4),
            'rows': kwargs.get('rows', 1),
            'with_container': kwargs.get('with_container', True),
        }
    )
    if 'block_title' in kwargs:
        context['block_title'] = kwargs['block_title']
    return context


@register.inclusion_tag('catalog/tags/catalog-dropdown-menu.html', takes_context=True)
def render_catalog_dropdown_menu(context):
    context['categories'] = get_published_categories(0)
    return context


@register.inclusion_tag(
    'catalog/tags/recently-watched-products.html', takes_context=True
)
def render_recently_watched(context):
    if config.RECENTLY_WATCHED_BLOCK_IS_ENABLED:
        data = context.request.session.get(RECENTLY_WATCHED_SESS_KEY)
        if data:
            products = Product.objects.filter(slug__in=data)
            if 'product_slug' in context.request.resolver_match.kwargs:
                products = products.exclude(
                    slug=context.request.resolver_match.kwargs['product_slug']
                )
            context['products'] = products

    return context


@register.inclusion_tag('catalog/tags/product-modifications.html', takes_context=True)
def render_product_modifications(context, product):
    if product.modifications.count() <= 1:
        return

    params = defaultdict(dict)
    product_params_ids = product.params.values_list('parameter_id', flat=True)

    modes_qs = (
        product.modifications.filter(
            (
                Q(
                    params__parameter__data_type='str',
                    params__parameter_value__value_str__isnull=False,
                )
                | Q(
                    params__parameter__data_type='decimal',
                    params__value_decimal__isnull=False,
                )
            ),
            params__parameter__use_for_modes=True,
            params__parameter_id__in=product_params_ids,
        )
        .values(
            'pk',
            'params__parameter__data_type',
            'params__value_decimal',
            'params__parameter__name',
            'params__parameter_value__value_str',
            'params__parameter__mode_widget',
            'params__parameter_id',
            'slug',
            'params__position',
        )
        .order_by('params__position', 'params__parameter_value__position')
    )

    for p in modes_qs:

        field = params[p['params__parameter__name']]
        if 'data_type' not in field:
            field['data_type'] = p['params__parameter__data_type']
        if 'type' not in field:
            field['type'] = p['params__parameter__mode_widget']
        if 'param_id' not in field:
            field['param_id'] = p['params__parameter_id']
        if 'choices' not in field:
            field['choices'] = []
        if p['pk'] == product.pk and 'position' not in field:
            field['position'] = p['params__position']

        if p['params__parameter__data_type'] == 'str':
            if p['params__parameter_value__value_str'] not in field['choices']:
                field['choices'].append(p['params__parameter_value__value_str'])
        elif p['params__parameter__data_type'] == 'decimal':
            if p['params__value_decimal'] not in field['choices']:
                field['choices'].append(p['params__value_decimal'])

    product_params_values = defaultdict(list)
    for dtype, name, val_str, val_decimal in product.params.values_list(
        'parameter__data_type',
        'parameter__name',
        'parameter_value__value_str',
        'value_decimal',
    ):
        value = val_str if dtype == 'str' else val_decimal
        product_params_values[name].append(value)

    mode_params = dict(sorted(params.items(), key=lambda x: x[1].get('position', 0)))

    context.update(
        {
            'current_product': product,
            'mode_params': mode_params,
            'active_values': dict(product_params_values),
        }
    )

    return context


@register.inclusion_tag('catalog/tags/subcategories-buttons.html', takes_context=True)
def render_subcategories_top_nav(context, category=None):
    if not any(
        (
            config.CATALOG_SHOW_CHILDS_IN_PARENT,
            config.CATALOG_PRODUCT_LIST_ON_INDEX_PAGE,
        )
    ):
        return

    qs = Category.objects.filter(published=True)

    if category:
        qs = qs.filter(parent=category)
    else:
        qs = qs.filter(parent__isnull=True)
    context['subcategories'] = qs
    return context


def get_product_units_avail(context, product):
    '''
    Колличество доступных единиц товара.
    '''
    if config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE:
        return float('inf')

    location = get_context_location(context)
    return product.available_items_count(location)


@register.simple_tag(takes_context=True)
def product_units_avail(context, product):
    return get_product_units_avail(context, product)


@register.inclusion_tag('catalog/tags/product-listing.html', takes_context=True)
def render_product_listing(context, products, category=None):
    context['products'] = products
    if category:
        context['items_per_row'] = getattr(
            category, 'products_per_row', config.CATEGORY_PRODUCTS_PER_ROW
        )
    return context


@register.filter(takes_context=True)
def multiplicity_price(price, product):
    if price and product.multiplicity != 1:
        price *= product.multiplicity
        if not config.PRICE_WITH_PENNIES:
            price = round(price)
    return price


@register.inclusion_tag('catalog/teasers/teaser-list.html', takes_context=True)
def render_teaser_list(context, products, category=None):
    context['products'] = products
    context['teaser_product_category'] = category
    if category:
        context['items_per_row'] = getattr(
            category, 'products_per_row', config.CATEGORY_PRODUCTS_PER_ROW
        )
    return context


@register.simple_tag(takes_context=True)
def slider_constructor_dataset(context, **kwargs):
    output = (
        f'data-slides="{config.SLIDER_CONSTRUCTOR__DATA_SLIDES}" '
        f'data-sm-slides="{config.SLIDER_CONSTRUCTOR__DATA_SM_SLIDES}" '
        f'data-md-slides="{config.SLIDER_CONSTRUCTOR__DATA_MD_SLIDES}" '
        f'data-lg-slides="{config.SLIDER_CONSTRUCTOR__DATA_LG_SLIDES}" '
        f'data-test="{config.SLIDER_CONSTRUCTOR__DATA_LG_SLIDES}" '
        f'data-xl-slides="{config.SLIDER_CONSTRUCTOR__DATA_XL_SLIDES}"'
    )
    if kwargs:
        output += ' '
        output += ' '.join([f'{k.replace("_", "-")}="{v}"' for k, v in kwargs.items()])
    return mark_safe(output)


@register.simple_tag(takes_context=True)
def teaser_list_grid_classes(context, **kwargs):
    output = (
        'd-grid gap-grid '
        f'grid-columns-{config.SLIDER_CONSTRUCTOR__DATA_SLIDES} '
        f'grid-columns-lg-{config.SLIDER_CONSTRUCTOR__DATA_LG_SLIDES} '
        f'grid-columns-md-{config.SLIDER_CONSTRUCTOR__DATA_MD_SLIDES} '
        f'grid-columns-sm-{config.SLIDER_CONSTRUCTOR__DATA_SM_SLIDES} '
        f'grid-columns-xl-{config.SLIDER_CONSTRUCTOR__DATA_XL_SLIDES}'
    )

    if kwargs:
        output += ' '
        output += ' '.join([f'{k.replace("_", "-")}="{v}"' for k, v in kwargs.items()])
    return mark_safe(output)


@register.inclusion_tag('catalog/tags/related-products-calc.html', takes_context=True)
def render_related_products_calc(context, product, show_title=True):
    if config.RELATED_PRODUCTS_DISPLAY_VARIANT == 'calculator':
        rel_product_qs = ProductRelated.objects.filter(
            ref=product, product__published=True
        )

        context['cart'] = Cart.from_request(context['request'])
        context['calc_show_title'] = show_title

        calc_related_products = (
            item.product
            for item in rel_product_qs.distinct()
            .exclude_by_modification_code()
            .only('product')
        )
        context['calc_related_products'] = calc_related_products

    return context


@register.simple_tag(takes_context=True)
def product_final_price(context, product):
    request = context.get('request')
    return product.get_final_price(request.user, request.location)


@register.inclusion_tag('catalog/tags/product-sale-badge.html', takes_context=True)
def render_product_sale_badge(context, product, for_teaser=False, badge_classes=None):
    context['discount_percent'] = None

    if not product.old_price or any((product.price_from, product.price_from_to)):
        return context

    request = context['request']
    price = product.get_final_price(request.user, request.location)

    if price and price < product.old_price:
        context['discount_percent'] = round((1 - (price / product.old_price)) * 100)

    context['for_teaser'] = for_teaser
    context['badge_classes'] = badge_classes

    return context


def get_product_prices_dict(request, product, category=None):
    '''
    https://redmine.fancymedia.ru/issues/10356
    верстка:
         https://luzhetskiy.github.io/stroyker-k1-html-dev/product/product-default-v1/product-default-v1-legacy__new.html

    1. Заполнена только цена
    2. Есть пересчет в другую единицу измерения
    это когда поле "Кратность упаковки:" у товара не равно 1
    в этом случае блок с ценой дублируется с другой единицей измерения
    (следующие сценарии со старой ценой или онлайн ценой тоже дублируются)
    не дублируется только блок с графиком цены

    3. У товара есть старая цена
    старая перечеркнута, актуальная - обычная большая

    4. Есть онлайн цена (включена настройка онлайн цены)
    крупно показывается онлайн цена, лейбл перед ценой "Онлайн цена:"
    серым мелко - обычная цена
    если есть "старая цена", то она перечеркнута

    5. Есть персональная цена (может быть только у авторизованного пользователя и если настроена система скидок)
    крупно показывается персональная цена, перед ценой лейбл "Персональная цена:"
    если в настройках есть и онлайн цена и у юзера персональная, то лейбл все равно "Персональная",
    а выводиться будет та цена, которая выгодней (т.е. меньше)

    6. есть цена, но нет в наличии
    этот сценарий актуален только если настройка PRODUCT_ALLOW_SALE_NOT_AVAIBLE = False
    кнопка "в корзину" заменяется на кнопку "Узнать о наличии" с анкерной ссылкой на форму в подвале
    лейбл "Цена" переименовывается в "Архивная цена"
    сама цена бледно-серого цвета

    7. нет цены (наличие тут уже не важно есть или нет)
    кнопка "в корзину" заменяется на кнопку "узнать цену" с анкерной ссылкой на форму в подвале

    upd (по лейблам)
    https://redmine.fancymedia.ru/issues/10874
    '''
    output = {}
    product_price = getattr(
        product.location_price_object(request.location), 'currency_price', None
    )
    main_price = product_price

    personal_price = online_price = None

    # последние изменения по мотивам задачи
    # https://redmine.fancymedia.ru/issues/10874
    if request.user.is_authenticated:
        user_price = product.get_final_price(request.user, request.location)

        if user_price and user_price < main_price:
            main_price = user_price
            if request.user.has_discount:
                personal_price = user_price
            else:
                online_price = user_price
    else:
        online_price = product.online_price(
            request.user, request.location, category=category
        )
        try:
            # на случай, если в main_price придет не цифра
            if online_price and online_price < main_price:
                main_price = online_price
            else:
                online_price = None
        except TypeError:
            pass

    output = {
        'main': main_price,
        'product_price': product_price,
        'personal': personal_price,
        'online': online_price,
    }

    if product.multiplicity and product.multiplicity != 1:
        output['multiplicity_by_unit'] = main_price * product.multiplicity
        if product_price and main_price < product_price:
            output['multiplicity_by_unit_orig'] = product_price * product.multiplicity
        if product.old_price:
            output['multiplicity_by_unit_old'] = (
                product.old_price * product.multiplicity
            )
    return output


@register.inclusion_tag('catalog/price_block/price-block-base.html', takes_context=True)
def render_product_price_block(context, product):
    context['product'] = product

    if product.has_price_from_to:
        # признак "цена от-до"
        # https://redmine.fancymedia.ru/issues/10358
        # если признак будет установлен, то нужно показать две цены:
        # цена от: (это будет поле "цена" у товара)
        # цена до: (это будет поле "старая цена" у товара)
        # будет работать только если у товара заполнено обе цены
        # кнопка "в корзину" должна измениться на кнопку "узнать цену" и работать аналогично кейсу,
        # когда у товара нет цены, т.е. перебрасывать юзера на форму в подвале с подстановкой в коммент названия товара
        context['template'] = 'catalog/price_block/price-block-fromto.html'
        return context

    context['template'] = 'catalog/price_block/price-block-orig.html'

    request = context['request']

    context['prices'] = get_product_prices_dict(request, product)
    context['availability'] = {
        'is_avail': product.is_available(request.location),
        'units_count': get_product_units_avail(context, product),
    }

    return context


def get_teaser_price_label(prices_dict):
    if prices_dict.get('personal'):
        return config.PERSONAL_PRICE_LABEL
    if prices_dict.get('online'):
        return config.ONLINE_PRICE_LABEL_TEXT


@register.inclusion_tag('catalog/teasers/product-teaser.html', takes_context=True)
def render_product_teaser_new(context, product, teaser_product_category=None):
    request = context['request']
    template = f'catalog/teasers/teaser-v-{config.PRODUCT_TEASER_VARIANT}.html'
    context['template'] = template
    context['product'] = product
    context['teaser_product_category'] = teaser_product_category
    context['config'] = config

    prices_dict = get_product_prices_dict(request, product, teaser_product_category)
    context['prices'] = prices_dict
    context['price_label'] = get_teaser_price_label(prices_dict)
    return context


@register.inclusion_tag('catalog/tags/related-products.html', takes_context=True)
def render_related_products(context, product, show_title=True):
    related_products = None
    # https://redmine.fancymedia.ru/issues/10611
    if config.RELATED_PRODUCTS_DISPLAY_VARIANT == 'carousel':
        rel_products_main = ProductRelated.objects.filter(
            ref=product, product__published=True
        )

        # https://redmine.fancymedia.ru/issues/11825
        if not config.RELATED_PRODUCTS_SHOW_NOT_AVAIBLE:
            rel_products_main = rel_products_main.filter(
                product__stocks_availability__available__gt=0
            )

        related_products = {
            item.product
            for item in rel_products_main.distinct()
            .exclude_by_modification_code()
            .only('product')
        }
        context['related_products_main'] = related_products

    context['related_show_title'] = all((show_title, related_products))

    return context


@register.inclusion_tag(
    'catalog/tags/category-related-products.html', takes_context=True
)
def render_category_related_products(context, product, limit=10, show_title=True):

    rel_products_category = None

    if product.category:
        rel_categories = tuple(
            product.category.related_categories.filter(published=True)
        )
        all_products_qs = (
            Product.objects.published()
            .filter(categories__in=rel_categories)
            .exclude_by_modification_code()
            .prefetch_related('categories')
            .order_by('?')
        )
        # https://redmine.fancymedia.ru/issues/11825
        if not config.RELATED_PRODUCTS_SHOW_NOT_AVAIBLE:
            all_products_qs = all_products_qs.filter(
                stocks_availability__available__gt=0
            )

        categories = defaultdict(list)
        for product in all_products_qs:
            for category in product.categories.all():
                if category in rel_categories:
                    categories[category].append(product)

        rel_products_category = []
        while len(rel_products_category) < limit:
            for category, products in list(categories.items()):
                if products:
                    rel_products_category.append(products.pop(0))
                else:
                    del categories[category]
                if len(rel_products_category) == limit:
                    break
            if not categories:
                break

    if rel_products_category:
        context['related_products_category'] = rel_products_category

    context['related_show_title'] = show_title

    return context
