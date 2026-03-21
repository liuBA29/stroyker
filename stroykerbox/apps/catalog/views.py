from decimal import Decimal, InvalidOperation
import os
from collections import OrderedDict, defaultdict

from django.views.generic import TemplateView, DetailView, View
from django.views.generic.list import ListView
from django.db.models import F, Q, Value, IntegerField
from django.db.models.functions import Coalesce
from django.http import Http404, JsonResponse
from django.http.response import HttpResponse, HttpResponseBadRequest
from django.shortcuts import reverse, get_object_or_404, render
from django.utils.html import strip_tags
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.utils.decorators import method_decorator
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.utils.translation import ugettext as _
from django.views.generic import RedirectView
from django.conf import settings
from django.core.management import call_command
from django.views.decorators.csrf import csrf_exempt
from django.db.models.functions import Lower
from django.utils.timezone import now
from constance import config


from stroykerbox.apps.banners.utils import check_page_has_banners
from stroykerbox.apps.catalog.forms import FilterForm
from stroykerbox.apps.catalog.models import Category, Product
from stroykerbox.apps.catalog import RECENTLY_WATCHED_SESS_KEY
from stroykerbox.apps.utils.utils import clear_punctuation

from .resources import CatalogProductExportResource
from .utils import _all_equal, lat2cyr
from .models import Parameter
from .import_export import heavy_picture_products_export


PERIODS = {
    'month': _('Month'),
    'quarter': _('Quarter'),
    'year': _('Year'),
    'all_time': _('All time'),
}

PERIOD_DEFAULT = 'month'

LIST_VIEW_MODE_CLASSES = {
    1: '',  # defaul view - as tiles
    2: 'product-item--wide',  # as row
    3: 'product-item--line',  # profi-mode
}


def get_8march_index_context(request):
    """
    Контекст для главной страницы в дизайне 8march (категории-кружки, акции, сборные букеты).
    Используется в CatalogFrontpageView при USE_8MARCH_HEADER_FOOTER и в view_8march_design_test.
    """
    from django.urls import reverse

    location = getattr(request, 'location', None)

    def _format_price(value):
        if value in (None, ''):
            return ''
        try:
            amount = Decimal(value).quantize(Decimal('1'))
        except (InvalidOperation, TypeError, ValueError):
            return ''
        return f"{int(amount):,}".replace(',', ' ') + ' P'

    category_slots = (
        ('images/gotovaya-vitrina.png', 'Готовая витрина', 'ГОТОВАЯ<br>ВИТРИНА', 'gotovaya-vitrina'),
        ('images/monoduo-bukety.png', 'Моно букеты', 'МОНО<br>БУКЕТЫ', 'monoduo-bukety'),
        ('images/kompozicii.png', 'Композиции', 'КОМПОЗИЦИИ', 'kompozicii'),
        ('images/wow-effect.png', 'Эффектные букеты', 'ЭФФЕКТНЫЕ<br>БУКЕТЫ', 'wow-bukety'),
        ('images/fresh-buketi.png', 'Интерьерные букеты', 'ИНТЕРЬЕРНЫЕ<br>БУКЕТЫ', 'fresh-bukety'),
        ('images/podarki.png', 'Подарки', 'ПОДАРКИ', 'podarki'),
    )
    categories_8march = []
    for img, alt, label, slug in category_slots:
        try:
            url = reverse('catalog:category', kwargs={'category_slug': slug})
        except Exception:
            url = reverse('catalog:index')
        categories_8march.append({
            'url': url,
            'image': img,
            'alt': alt,
            'label': label,
        })

    promo_qs = Product.objects.filter(
        published=True, categories__slug='8-marta'
    ).prefetch_related('images').distinct()
    promo_products = []
    for product in promo_qs.order_by('-updated_at'):
        price_obj = product.location_price_object(location)
        main_price = (
            getattr(price_obj, 'currency_price', None)
            or getattr(price_obj, 'price', None)
            or product.currency_price
            or product.price
        )
        old_price = (
            getattr(price_obj, 'currency_old_price', None)
            or getattr(price_obj, 'old_price', None)
            or product.currency_old_price
            or product.old_price
        )
        main_price_fmt = _format_price(main_price)
        old_price_fmt = _format_price(old_price)
        image_url = ''
        if product.main_image and getattr(product.main_image, 'image', None):
            try:
                image_url = product.main_image.image.url
            except Exception:
                image_url = ''
        if not image_url:
            image_url = '/static/images/empty-product.svg'
        promo_products.append({
            'url': product.get_absolute_url() or reverse('catalog:index'),
            'image': image_url,
            'alt': product.name or 'Товар',
            'price': main_price_fmt,
            'old_price': old_price_fmt,
        })
        if len(promo_products) >= 24:
            break

    bouquets_qs = Product.objects.filter(
        published=True, images__isnull=False
    ).prefetch_related('images').distinct()
    bouquet_base = list(bouquets_qs.order_by('?')[:9])
    if not bouquet_base:
        bouquet_base = list(
            Product.objects.filter(published=True)
            .prefetch_related('images')
            .order_by('-updated_at')[:9]
        )
    bouquet_products = []
    if bouquet_base:
        while len(bouquet_products) < 9:
            for product in bouquet_base:
                price_obj = product.location_price_object(location)
                main_price = (
                    getattr(price_obj, 'currency_price', None)
                    or getattr(price_obj, 'price', None)
                    or product.currency_price
                    or product.price
                )
                image_url = ''
                if product.main_image and getattr(product.main_image, 'image', None):
                    try:
                        image_url = product.main_image.image.url
                    except Exception:
                        image_url = ''
                if not image_url:
                    image_url = '/static/images/empty-product.svg'
                bouquet_products.append({
                    'url': product.get_absolute_url() or reverse('catalog:index'),
                    'add_to_cart_url': reverse('cart:add_to_cart', kwargs={'product_pk': product.pk}),
                    'pk': product.pk,
                    'image': image_url,
                    'alt': product.name or 'Сборный букет',
                    'name': product.name or 'Сборный букет',
                    'price': _format_price(main_price),
                })
                if len(bouquet_products) >= 9:
                    break
    else:
        bouquet_products = [{
            'url': reverse('catalog:index'),
            'add_to_cart_url': '',
            'pk': None,
            'image': '/static/images/empty-product.svg',
            'alt': 'Сборный букет',
            'name': 'Сборный букет',
            'price': '',
        } for _ in range(9)]

    return {
        'categories_8march': categories_8march,
        'promo_products': promo_products,
        'bouquet_products': bouquet_products,
    }


class CatalogFrontpageView(TemplateView):
    """
    Site frontpage.
    """

    template_name = 'catalog/frontpage.html'

    def get_template_names(self):
        from stroykerbox.apps.customization.context_processors import _use_8march_header_footer
        if _use_8march_header_footer(self.request):
            return ['catalog/frontpage_8march.html']
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = (
            Product.objects.published().exclude_by_modification_code()[:12]
        )
        context['show_breadcrumbs'] = False

        from stroykerbox.apps.customization.context_processors import _use_8march_header_footer
        if _use_8march_header_footer(self.request):
            context.update(get_8march_index_context(self.request))

        if hasattr(self.request, 'seo'):
            self.request.seo.title.append(config.SITE_NAME)

        return context


class CatalogIndexView(ListView):
    """
    Домашняя страница каталога.

    https://redmine.fancymedia.ru/issues/10619#note-10
    Логика отображения:

    1) Дефолтный каталог, когда у нас не проставлены галочки на показе дочерних
    категорий на странице родителя CATALOG_SHOW_CHILDS_IN_PARENT и товаров на
    основной странице каталога CATALOG_PRODUCT_LIST_ON_INDEX_PAGE
    Т.е. у нас основной каталог с превью категорий https://skr.sh/sNytup52eN8

        п.1.1
        Категории, которые указаны как "Контейнер" в настройках категории,
        должны отображать внутри другие категории "дочки" (не отображают товары) и
        "Каталог продукции" со всеми категориями https://skr.sh/sNybf7r7Cdo https://skr.sh/sNynjxFIiK6

        п.1.2
        Категории, которые не указаны как "Контейнер", отображают товары и
        фильтр по-умолчанию https://skr.sh/sNybyhrN7i2 , или, если проставлена
        галочка на "Показывать родственные категории в сайдбаре" в настройках категории,
        отображать соседние дочки в меню https://skr.sh/sNyKVPKj4DX
        https://skr.sh/sNyoGulYzVq https://skr.sh/sNynElSshIs
        В таких категориях при отсутствии товаров выходит заглушка "Раздел находится
        на стадии заполнения." (сейчас её нет на действительно пустых категориях
          https://skr.sh/sNywPguM9gc ) https://skr.sh/sNyumJhmrQ2 и "каталог продукции" с родственными категориями

        п.1.3
        Категории, которые не указаны как "Контейнер", но они являются категориями
        первого уровня: т.к. все категории для неё соседние - отображает товары
        и весь каталог продукции при проставленной настройке "Показывать родственные
        категории в сайдбаре", по-умолчанию - фильтр.
    """

    def get_queryset(self):
        if config.CATALOG_PRODUCT_LIST_ON_INDEX_PAGE:
            return Product.objects.published().exclude_by_modification_code()
        return Category.objects.filter(published=True, level=0)

    def get_template_names(self):
        if config.CATALOG_PRODUCT_LIST_ON_INDEX_PAGE:
            if config.CATALOG_CHILDS_IN_PARENT_NAV == 'accordion':
                return 'catalog/index-by-products-sidebar.html'
            return 'catalog/index-by-products.html'
        return 'catalog/index-by-categories.html'

    def get_context_object_name(self, object_list):
        if config.CATALOG_PRODUCT_LIST_ON_INDEX_PAGE:
            return 'products'
        return 'categories'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self.request, 'seo'):
            self.request.seo.breadcrumbs.append(('', config.CATALOG_MENU_TITLE))
            if self.request.seo.seo_text:
                context['seo_text'] = self.request.seo.seo_text
        return context

    def get_paginate_by(self, queryset):
        """
        Get the number of items to paginate by, or ``None`` for no pagination.
        """
        if config.CATALOG_PRODUCT_LIST_ON_INDEX_PAGE:
            return config.PRODUCTS_COUNT_ON_PAGE
        return super().get_paginate_by(queryset)


class DetailPublishedBase(DetailView):

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(published=True)


class CategoryView(DetailPublishedBase):
    """
    Страница конкретной категории.

    https://redmine.fancymedia.ru/issues/10619#note-10
    Логика отображения (для всех страниц каталога и его категорий в целом):

    1) Дефолтный каталог, когда у нас не проставлены галочки на показе дочерних категорий на странице родителя
    CATALOG_SHOW_CHILDS_IN_PARENT и товаров на основной странице каталога CATALOG_PRODUCT_LIST_ON_INDEX_PAGE
    Т.е. у нас основной каталог с превью категорий https://skr.sh/sNytup52eN8
        п.1.1
        Категории, которые указаны как "Контейнер" в настройках категории,
        должны отображать внутри другие категории "дочки" (не отображают товары)
        и "Каталог продукции" со всеми категориями https://skr.sh/sNybf7r7Cdo https://skr.sh/sNynjxFIiK6
        п.1.2
        Категории, которые не указаны как "Контейнер", отображают товары и фильтр
        по-умолчанию https://skr.sh/sNybyhrN7i2 , или, если проставлена галочка
        на "Показывать родственные категории в сайдбаре" в настройках категории,
        отображать соседние дочки в меню https://skr.sh/sNyKVPKj4DX
        https://skr.sh/sNyoGulYzVq https://skr.sh/sNynElSshIs
        В таких категориях при отсутствии товаров выходит заглушка
        "Раздел находится на стадии заполнения." (сейчас её нет на действительно
        пустых категориях https://skr.sh/sNywPguM9gc ) https://skr.sh/sNyumJhmrQ2
        и "каталог продукции" с родственными категориями
        п.1.3
        Категории, которые не указаны как "Контейнер", но они являются категориями
        первого уровня: т.к. все категории для неё соседние - отображает товары
        и весь каталог продукции при проставленной настройке
        "Показывать родственные категории в сайдбаре", по-умолчанию - фильтр.

    2) Каталог, когда у нас проставлена галочка на показе дочерних категорий на
    странице родителя CATALOG_SHOW_CHILDS_IN_PARENT и вид навигации CATALOG_CHILDS_IN_PARENT_NAV
    "аккордеон": на основной странице каталога - превью категорий https://skr.sh/sNyUMNRg2Nh
        п.2.1
        Категории, которые указаны как "Контейнер" в настройках категории,
        отображают не "дочек", а товары этих "дочек" и "Каталог продукции" со
        всеми категориями https://skr.sh/sNytcqpEj6O
        п.2.2
        Категории, которые не указаны как "Контейнер", работают аналогично п.1.2
        п.2.3
        Категории, которые не указаны как "Контейнер", но они являются категориями
        первого уровня: аналогично п.1.3

    3) Каталог, когда у нас проставлена галочка на показе дочерних категорий на
    странице родителя CATALOG_SHOW_CHILDS_IN_PARENT и вид навигации CATALOG_CHILDS_IN_PARENT_NAV
    "кнопки сверху": основной каталог с превью категорий, без кнопок как сейчас https://skr.sh/sNyVb7tlRJ1
        п.3.1
        Категории, которые указаны как "Контейнер" в настройках категории,
        отображают не "дочек", а товары этих "дочек" и кнопки категорий дочек сверху,
        без фильтра или каталога продукции https://skr.sh/sNyyPWzez5u
        п.3.2
        Категории, которые не указаны как "Контейнер",
        п.3.3
        Категории, которые не указаны как "Контейнер", но они являются категориями
        первого уровня: аналогично п.1.3
    """

    model = Category
    level = 0
    context_object_name = 'category'
    slug = ''

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        self.category_slug = self.kwargs.get('category_slug', None)
        self.subcategory_slug = self.kwargs.get('subcategory_slug', None)

        if self.subcategory_slug:
            slug_for_search, level = self.subcategory_slug, 1
        else:
            slug_for_search, level = self.category_slug, 0

        self.level = level
        self.slug = slug_for_search

    def get_object(self, queryset=None):

        if queryset is None:
            queryset = self.get_queryset()

        if not self.slug:
            raise AttributeError(
                f'Generic detail view {self.__class__.__name__} must be called with '
                'either an object slug.'
            )

        queryset = queryset.filter(slug=self.slug)
        if self.level:
            queryset = queryset.filter(parent__slug=self.category_slug)

        try:
            obj = queryset.get()
        except Category.DoesNotExist:
            raise Http404(
                f'No {queryset.model._meta.verbose_name} ' 'found matching the query'
            )
        except Category.MultipleObjectsReturned:
            obj = queryset.first()

        return obj

    def get_template_names(self):

        has_children = self.object.children.exists()

        if not self.subcategory_slug and not has_children:
            return 'catalog/category-child-page.html'

        is_root = any((self.level == 0, self.subcategory_slug is None, has_children))

        if is_root:
            if config.CATALOG_SHOW_CHILDS_IN_PARENT:
                return 'catalog/category-root-with-product-list.html'
            if has_children:
                return 'catalog/category-root-page.html'

        return 'catalog/category-child-page.html'

    def render_to_response(self, context, **kwargs):
        """Allow AJAX requests to be handled more gracefully"""
        if self.request.is_ajax():
            return JsonResponse(
                {'count': context.get('products_filter_count', None)}, safe=False
            )
        return super().render_to_response(context, **kwargs)

    @property
    def has_form_params(self):
        get_params = set(getattr(self.request, 'GET', {}).keys())
        service_params = {'page', 'sort_field', 'price_sort'}
        return bool(get_params - service_params)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.level or not self.object.is_container:
            context['hide_sidebar'] = bool(
                not config.CATALOG_PAGE_SHOW_SIDEBAR
                and not check_page_has_banners(self.request.path)
            )

        list_view_mode = int(
            self.request.COOKIES.get('list_view_mode', config.CATALOG_LIST_VIEW_MODE)
        )

        context['list_view_mode'] = list_view_mode
        context['list_view_mode_class'] = LIST_VIEW_MODE_CLASSES[list_view_mode]

        products_on_page = config.PRODUCTS_COUNT_ON_PAGE

        location = getattr(self.request, 'location', None)

        current_page = self.request.GET.get('page', 1)

        form = FilterForm(self.object, location, self.request.GET)

        category_products_qs = self.object.products.published()

        has_form_params = self.has_form_params

        # https://redmine.fancymedia.ru/issues/12233
        order_mods_by_priority = bool(not has_form_params)

        if self.level == 0 and config.CATALOG_SHOW_CHILDS_IN_PARENT:

            slugs_for_filter = [self.object.slug] + list(
                self.object.get_published_children().values_list('slug', flat=True)
            )
            category_products_qs = (
                Product.objects.published()
                .filter(categories__slug__in=slugs_for_filter)
                .exclude_by_modification_code(order_mods_by_priority)
                .order_by('position', 'price', '-updated_at')
                .catalog_order()
            )

        category_products_count = category_products_qs.count()

        price_sort = self.request.GET.get('price_sort', None)
        sort_params = self.request.GET.getlist('sort_field')

        if self.level > 0 or category_products_count > 0:

            if has_form_params and form.is_valid():
                products = form.get_filtered_products()
            else:
                products = self.object.get_descendant_products()

            if price_sort or sort_params:
                order_by = []
                if price_sort == 'price__asc':
                    # https://redmine.nastroyker.ru/issues/15104#note-5
                    products = products.annotate(
                        price_value=Coalesce(
                            F('price'),
                            Value(1000000),
                            output_field=IntegerField(),
                        )
                    )
                    order_by.append('price_value')
                elif price_sort == 'price__desc':
                    # https://redmine.nastroyker.ru/issues/15104#note-5
                    products = products.annotate(
                        price_value=Coalesce(
                            F('price'), Value(-1), output_field=IntegerField()
                        )
                    )
                    order_by.append('-price_value')
                elif 'name' in sort_params:
                    order_by.append(Lower('name'))

                if 'availability' in sort_params:
                    order_by.append('-stocks_availability__available')
                    products = products.filter(stocks_availability__available__gt=0)
                if order_by:
                    products = products.order_by(*order_by)
            else:
                if not has_form_params and config.PRODUCT_ONLY_AVAIL_BY_DEFAULT:
                    products = products.filter(stocks_availability__available__gt=0)

                products = products.catalog_order()
        else:
            products = category_products_qs.filter(is_hit=True)

        products_filter_count = products.count()
        products = products.exclude_by_modification_code()

        products_paginator = Paginator(products, products_on_page)

        # Catch invalid page numbers
        try:
            paginated_products = products_paginator.page(current_page)
        except (PageNotAnInteger, EmptyPage):
            paginated_products = products_paginator.page(1)

        context['filter_form'] = form
        context['products'] = paginated_products
        context['products_count'] = category_products_count
        context['products_filter_count'] = products_filter_count
        context['seo_text'] = self.object.seo_text
        context['sort_params'] = sort_params

        if hasattr(self.request, 'seo'):
            # override seo meta tags
            self.request.seo.override_seo_tags_with_catalog_filters(self.object, form)

            # add full path by categories chain to breadcrumbs
            self.request.seo.breadcrumbs.append(
                (reverse('catalog:index'), config.CATALOG_MENU_TITLE)
            )
            if self.object.parent:
                self.request.seo.breadcrumbs.append(
                    (self.object.parent.get_absolute_url(), self.object.parent.name)
                )
            self.request.seo.breadcrumbs.append(('', self.object.name))
            if self.request.seo.seo_text:
                context['seo_text'] = self.request.seo.seo_text

        return context


class RedirectToProductView(RedirectView):
    """
    Redirect for old urls with category slugs in paths.
    """

    permanent = True

    def get_redirect_url(*args, **kwargs):
        product_slug = kwargs.get('product_slug')
        return reverse(
            'catalog:product_view',
            kwargs={
                'product_slug': product_slug,
            },
        )


class ProductView(DetailPublishedBase):
    model = Product
    slug_url_kwarg = 'product_slug'
    context_object_name = 'product'

    def get_template_names(self):
        if config.PRODUCT_PAGE_TEMPLATE_VARIANT != 'default':
            # https://redmine.nastroyker.ru/issues/19766
            return f'catalog/product-page-{config.PRODUCT_PAGE_TEMPLATE_VARIANT}.html'

        if config.PRODUCT_CARD_VARIANT == 'default_no_tabs':
            return 'catalog/product-page-no-tabs.html'
        return 'catalog/product-page.html'

    def get(self, request, *args, **kwargs):
        if config.RECENTLY_WATCHED_BLOCK_IS_ENABLED:
            if (
                RECENTLY_WATCHED_SESS_KEY not in request.session
                and 'product_slug' in kwargs
            ):
                request.session[RECENTLY_WATCHED_SESS_KEY] = set()
            request.session[RECENTLY_WATCHED_SESS_KEY].add(kwargs['product_slug'])
            request.session.modified = True
        return super().get(request, args, kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        product = self.object
        category = product.category
        context['has_documents'] = product.certificates.exists()

        if category:
            next_prev_qs = category.products.filter(published=True).order_by(
                '-created_at'
            )
            next_qs = next_prev_qs.filter(created_at__gt=product.created_at)
            if next_qs.exists():
                context['next_product_url'] = next_qs.first().get_absolute_url()
            prev_qs = next_prev_qs.filter(created_at__lt=product.created_at)
            if prev_qs.exists():
                context['prev_product_url'] = prev_qs.first().get_absolute_url()

        if self.request.user.is_authenticated:
            period = self.request.GET.get('price_history_period')
            if period not in PERIODS:
                period = PERIOD_DEFAULT
            context['period_checked'] = period
            context['label_period'] = PERIODS[period]
            prices_data = self.object.get_history_prices(
                location=self.request.location, choiced_period=period
            )
            if prices_data:
                context['chart_data'] = True
                context['chart_prices'] = prices_data['prices']
                context['chart_price_dates'] = prices_data['dates']

        context['online_price'] = self.object.online_price(
            self.request.user, self.request.location
        )

        if hasattr(self.request, 'seo'):
            # add full path by categories chain to breadcrumbs
            self.request.seo.breadcrumbs.append(
                (reverse('catalog:index'), config.CATALOG_MENU_TITLE)
            )
            if self.object.category:
                for c in self.object.category.get_ancestors(include_self=True):
                    self.request.seo.breadcrumbs.append((c.get_absolute_url(), c.name))

            self.request.seo.title.append(self.object.name)

        def filter_delivery_props(delivery_prop):
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

        context['delivery_props'] = list(filtered_delivery_props)

        return context


class ProductSearchResult(ListView):
    """
    Display a page with a product list filtered by the search query.
    """

    model = Product
    paginate_by = config.PRODUCTS_COUNT_ON_PAGE
    context_object_name = 'products'
    template_name = 'catalog/products-search-result.html'
    template_name_ajax = 'catalog/ajax-products-search-result.html'

    def get_template_names(self):
        if self.request.is_ajax():
            return [self.template_name_ajax]
        return super().get_template_names()

    def get_paginate_by(self, queryset):
        if self.request.is_ajax():
            return config.PRODUCTS_COUNT_ON_PAGE * 2
        return self.paginate_by

    def get_search_queryset(self):
        qs = Product.objects.published().exclude_by_modification_code().catalog_order()
        if not config.SEARCH__OUT_OF_STOCK:
            qs = qs.filter(stocks_availability__isnull=False)

        if config.SEARCH__USE_FULLTEXT:
            query = SearchQuery(
                self.keywords,
                config='russian',
                search_type=config.SEARCH__FULLTEXT_TYPE,
            )
            if self.keywords_alter:
                query |= SearchQuery(
                    self.keywords_alter, config='russian', search_type='phrase'
                )

            qs = (
                qs.filter(search_document=query)
                .annotate(rank=SearchRank(F('search_document'), query))
                .order_by('-rank')
            )
        else:
            filter = (
                Q(name__icontains=self.keywords)
                | Q(sku__icontains=self.keywords)
                | Q(search_words__icontains=self.keywords)
            )
            if self.keywords_alter:
                filter |= (
                    Q(name__icontains=self.keywords_alter)
                    | Q(sku__icontains=self.keywords_alter)
                    | Q(search_words__icontains=self.keywords)
                )
            qs = qs.filter(filter)

        return qs

    def get_queryset(self):
        keywords = self.request.GET.get('q')
        self.keywords = clear_punctuation(strip_tags(keywords).strip())
        self.keywords_alter = (
            lat2cyr(self.keywords) if config.SEARCH__USE_LAT2CYR else None
        )
        if self.keywords:
            qs = self.get_search_queryset()
            if qs.exists():
                sort_field = self.request.GET.get('sort_field', None)
                if sort_field and Product.field_exists(sort_field.split('__')[0]):
                    if sort_field == 'is_hit':
                        sort_field = '-is_hit'
                    elif sort_field == 'price__asc':
                        sort_field = 'price'
                    elif sort_field == 'price__desc':
                        sort_field = '-price'
                    qs = qs.order_by(f'{sort_field}')
            return qs
        return ''

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.keywords:
            context['keywords'] = self.keywords
            context['num_results'] = self.get_queryset().count()

        if hasattr(self.request, 'seo'):
            self.request.seo.breadcrumbs.append(
                (reverse('catalog:index'), config.CATALOG_MENU_TITLE)
            )
            self.request.seo.breadcrumbs.append(('', _('Search Results')))

        return context


@method_decorator(login_required, name='dispatch')
class AjaxChartPrices(View):
    http_method_names = ['post']

    def post(self, request, **kwargs):
        if request.is_ajax():
            product_id = int(request.POST.get('product_id'))
            period = request.POST.get('period')
            product = Product.objects.get(pk=product_id)
            prices_data = product.get_history_prices(
                choiced_period=period, location=request.location
            )
            context = {
                'success': True,
                'chart_prices': prices_data['prices'],
                'period_checked': period,
                'label_period': PERIODS[period],
                'chart_price_dates': prices_data['dates'],
            }
            return JsonResponse(context, safe=False)


def export_category_products_xls(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    dataset = CatalogProductExportResource().export(request=request, category=category)
    response = HttpResponse(content_type='application/vnd.ms-excel')
    # response['Content-Disposition'] = 'attachment; filename="ThePythonDjango.csv"'
    response['Content-Disposition'] = f'attachment; filename={category_slug}.xls'
    response.write(dataset.xls)
    return response


# Product comparison.
# Based on the idea from bunnylove.ru
def comparison_add(request):
    if request.POST.get('product_id') and request.POST['product_id'].isdigit():
        product_id = int(request.POST['product_id'])
        if not request.session.get('comparision'):
            request.session['comparision'] = []
        if product_id not in request.session['comparision']:
            request.session['comparision'].append(product_id)
            request.session.save()
        return JsonResponse(request.session['comparision'], safe=False)
    return HttpResponseBadRequest()


def comparison_del(request):
    if request.POST.get('product_id') and request.POST['product_id'].isdigit():
        product_id = int(request.POST['product_id'])
        if not request.session.get('comparision'):
            request.session['comparision'] = []
        elif product_id in request.session['comparision']:
            request.session['comparision'].remove(product_id)
            request.session.save()
        return JsonResponse(request.session['comparision'], safe=False)
    return HttpResponseBadRequest()


def comparison(request):
    products = []
    products_qs = (
        Product.objects.filter(pk__in=request.session.get('comparision', []))
        .exclude_by_modification_code()
        .prefetch_related('category')
    )

    products_by_categories = defaultdict(set)
    for product in products_qs:
        products_by_categories[product.category].add(product)

    # Sort by the number of products DESC, category name ASC.
    categories_sorted = sorted(
        products_by_categories.items(), key=lambda item: (-len(item[1]), item[0].name)
    )
    categories_filtered = OrderedDict()
    for i, (category, products) in enumerate(categories_sorted):  # type: ignore
        is_subset = False
        # TODO: find a better than a quadratic time algorithm.
        for filtered_products in categories_filtered.values():
            if products.issubset(filtered_products):  # type: ignore
                is_subset = True
                break

        if not is_subset:
            categories_filtered[category] = products

    parameters = OrderedDict()
    current_category = next(iter(categories_filtered)) if categories_filtered else None
    diff_only = bool(request.GET.get('diff_only', False))
    if categories_filtered:
        requested_category_id = request.GET.get('category_id')
        if requested_category_id and requested_category_id.isdigit():
            category_found = False
            for category in categories_filtered:
                if category.pk == int(requested_category_id):
                    current_category = category
                    category_found = True
                    break

            if not category_found:
                return HttpResponseBadRequest(_('Invalid category ID'))

        products = categories_filtered[current_category]
        base_parameters_qs = Parameter.objects.filter(
            categoryparametermembership__category=current_category,
            categoryparametermembership__display=True,
            productparametervaluemembership__product__in=products,
        )

        for parameter in base_parameters_qs:
            parameters[parameter.name] = [None] * len(products)

        for index, product in enumerate(products):
            for parameter in product.params.select_related('parameter'):
                parameter_name = parameter.parameter.name
                if parameter_name not in parameters:
                    continue
                parameters[parameter_name][index] = parameter.value

        # Show diff-only parameters only if there is more than 1 product.
        if diff_only and len(products) > 1:
            parameters = OrderedDict(
                (name, values)
                for name, values in parameters.items()
                if not _all_equal(values)
            )

    context = {
        'products': products,
        'categories': categories_filtered,
        'parameters': parameters,
        'current_category': current_category,
        'diff_only': diff_only,
    }
    template = 'catalog/comparison.html'
    if request.is_ajax():
        template = 'catalog/comparison-content.html'
    if hasattr(request, 'seo'):
        request.seo.breadcrumbs.append((request.path, _('Products comparison')))
        request.seo.title.append(_('Products comparison'))
    return render(request, template, context=context)


def yml_export(request):
    yml_file = settings.YML_EXPORT_FILE_PATH
    if not os.path.isfile(yml_file):
        call_command('export_to_yml')

    try:
        response = HttpResponse(content_type='application/xml')
        response['Content-Disposition'] = (
            f'attachment; filename={os.path.basename(yml_file)}'
        )
        response.write(open(yml_file, 'rb').read())
    except Exception as e:
        return HttpResponseBadRequest(e)

    return response


@csrf_exempt
def ajax_get_product_mod_url(request, source_product_pk, mod_code):
    url = None
    qs = Product.objects.filter(modification_code=mod_code, published=True).exclude(
        pk=source_product_pk
    )

    params = request.POST.dict()
    active_param_id = params.pop('active_id', None)
    active_param_value = params.pop('active_value', None)
    datatype_is_string = params.pop('active_datatype', 'str') == 'str'

    if all((active_param_id, active_param_value)):
        qs = qs.filter(params__parameter_id=active_param_id)
        if datatype_is_string:
            qs = qs.filter(params__parameter_value__value_str=active_param_value)
        else:
            value = Decimal(active_param_value.replace(',', '.'))
            qs = qs.filter(params__value_decimal=value)
        if params:
            for id in params:
                new_qs = qs.filter(params__parameter_id=id)
                if datatype_is_string:
                    new_qs = new_qs.filter(
                        params__parameter_value__value_str=params.get(id, '')
                    )
                else:
                    new_value = (params.get(id, None) or '').replace(',', '.')
                    new_qs = new_qs.filter(params__value_decimal=Decimal(new_value))
                if new_qs.exists():
                    qs = new_qs
        obj = qs.first()
    if obj:
        url = obj.get_absolute_url()

    return JsonResponse({'url': url})


@staff_member_required
def heavy_picture_products_xml(request):
    data = heavy_picture_products_export('xls')
    filename = f'heavy_picture_products_{now().strftime("%Y-%m-%d")}.xls'
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename={filename}'
    response.write(data)
    return response
