from django.views.generic.list import ListView
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Q, Case, Value, When, IntegerField, FloatField, QuerySet
from django.utils.translation import ugettext as _
from django.utils.html import strip_tags
from django.core.cache import cache
from constance import config

from stroykerbox.apps.catalog.utils import lat2cyr
from stroykerbox.apps.catalog.models import Product
from stroykerbox.apps.staticpages.models import Page
from stroykerbox.apps.staticpages.utils import staticpage_search_enabled
from stroykerbox.apps.utils.utils import clear_punctuation

from .models import SearchQueryData, SearchWordAlias, SEARCH_ALIASES_CACHE_KEY
from .tasks import create_search_query_data_object


def save_query(cleaned_query: str, request) -> None:
    # https://redmine.fancymedia.ru/issues/13063
    params = {
        'query_string': cleaned_query,
        'meta_data': {
            k: v
            for k, v in request.META.items()
            if k.startswith(SearchQueryData.META_FOR_SAVE)
        },
    }
    if request.user:
        params['user_id'] = request.user.id

    create_search_query_data_object.delay(**params)


class SearchResult(ListView):
    """
    Display a page with a product list filtered by the search query.
    """

    paginate_by = config.PRODUCTS_COUNT_ON_PAGE
    context_object_name = 'products'
    template_name = 'search/search-result.html'
    template_name_ajax = 'search/ajax-search-result.html'
    template_name_ajax_custom_header = 'search/ajax-search-result-custom-header.html'
    queryset = Product.objects.published()
    result_product_ids = set()

    def get_keywords_aliases_list(self, keywords: str) -> list:
        aliases = cache.get(SEARCH_ALIASES_CACHE_KEY)
        if not aliases:
            aliases = SearchWordAlias.create_search_aliases_cache()

        output = []
        for word in keywords.split():
            if word in aliases:
                output += aliases[word]

        return output

    def get(self, request, *args, **kwargs):
        keywords = self.request.GET.get('q', '')
        self.keywords = clear_punctuation(strip_tags(keywords).strip()).lower()

        # https://redmine.nastroyker.ru/issues/15874
        self.keywords_aliases_list = self.get_keywords_aliases_list(self.keywords)
        self.keywords_alter = (
            lat2cyr(self.keywords) if config.SEARCH__USE_LAT2CYR else None
        )

        if not request.is_ajax():
            save_query(self.keywords, request)

        return super().get(request, args, kwargs)

    def get_queryset(self) -> QuerySet | str:
        qs: QuerySet | str = ''
        if self.keywords:
            qs = self.get_product_search_queryset()

            if qs.exists():
                price_sort = self.request.GET.get('price_sort', None)
                sort_params = self.request.GET.getlist('sort_field')

                if price_sort or sort_params:
                    if 'availability' in sort_params:
                        qs = qs.filter(stocks_availability__available__gt=0).order_by(
                            '-stocks_availability__available'
                        )
                    if price_sort == 'price__asc':
                        qs = qs.order_by('price_value_asc')
                    elif price_sort == 'price__desc':
                        qs = qs.order_by('-price_value_desc')

                    if 'is_hit' in sort_params:
                        qs = qs.filter(is_hit=True)

                self.result_product_ids = set(qs.values_list('id', flat=True))

                by_stock = self.request.GET.getlist('stock')
                if by_stock:
                    qs = qs.filter(stocks_availability__warehouse_id__in=by_stock)

        return qs

    def get_template_names(self):
        if self.request.is_ajax():
            if config.CUSTOM_HEADER_ID not in ('0', 0):
                return [self.template_name_ajax_custom_header]
            return [self.template_name_ajax]
        return super().get_template_names()

    def get_paginate_by(self, queryset):
        if self.request.is_ajax():
            return config.PRODUCTS_COUNT_ON_PAGE * 2
        return self.paginate_by

    def get_product_search_queryset(self):
        qs = Product.objects.filter(published=True)
        ordering = []

        # https://redmine.nastroyker.ru/issues/16012
        if config.SEARCH__PRODUCT_ORDER_BY_POSITION:
            ordering.append('position')

        if not config.SEARCH__OUT_OF_STOCK:
            qs = qs.filter(stocks_availability__isnull=False)

        if not config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE:
            qs = qs.annotate(
                available=Case(
                    When(stocks_availability__isnull=True, then=Value(0)),
                    then=(F('available') + F('stocks_availability__available')),
                    default=Value(0),
                    output_field=FloatField(),
                ),
            )
            ordering.append('-available')

        if config.SEARCH__USE_FULLTEXT:
            query = SearchQuery(
                self.keywords,
                config='russian',
                search_type=config.SEARCH__FULLTEXT_TYPE,
            )
            # https://redmine.nastroyker.ru/issues/15874
            if self.keywords_alter:
                self.keywords_aliases_list.append(self.keywords_alter)
            for item in self.keywords_aliases_list:
                if item:
                    query |= SearchQuery(item, config='russian', search_type='phrase')

            qs = qs.filter(search_document=query).annotate(
                rank=SearchRank(F('search_document'), query)
            )
            ordering.append('-rank')
        else:
            filter_main = filter_aliases = filter_alter = Q()

            for word in self.keywords.split():
                filter_main &= (
                    Q(name__icontains=word)
                    | Q(sku__icontains=word)
                    | Q(search_words__icontains=word)
                )
            if self.keywords_aliases_list:
                # https://redmine.nastroyker.ru/issues/15874
                for word in self.keywords_aliases_list:
                    filter_aliases &= Q(name__icontains=word) | Q(
                        search_words__icontains=word
                    )
            if self.keywords_alter:
                for word in self.keywords_alter.split():
                    filter_alter &= (
                        Q(name__icontains=word)
                        | Q(sku__icontains=word)
                        | Q(search_words__icontains=word)
                    )
            qs = qs.filter(filter_main | filter_aliases | filter_alter)

        qs = qs.annotate(
            available_img=Case(
                When(images__isnull=False, then=1),
                default=0,
                output_field=IntegerField(),
            ),
            price_value_desc=Case(  # сортировка по нисходящей
                When(Q(price__isnull=True) | Q(price=0), then=-1),
                default=F('price'),
                output_field=IntegerField(),
            ),
            price_value_asc=Case(  # сортировка по восходящей
                When(Q(price__isnull=True) | Q(price=0), then=99999999),
                default=F('price'),
                output_field=IntegerField(),
            ),
        ).distinct()

        output = qs.order_by(
            *ordering, 'price_value_asc', 'available_img', '-updated_at', 'sku'
        )
        return output

    def get_staticpage_search_queryset(self):
        # use only with postgres fulltext search
        if not config.SEARCH__USE_FULLTEXT:
            return []

        qs = Page.objects.filter(published=True)
        query = SearchQuery(
            self.keywords, config='russian', search_type=config.SEARCH__FULLTEXT_TYPE
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

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.keywords:
            context['keywords'] = self.keywords
            context['product_num_results'] = len(self.result_product_ids)
            if (
                config.SEARCH_SHOW_WAREHOUSE_FILTER
                and not config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE
            ):
                context['result_product_ids'] = self.result_product_ids
                context['use_stock_filter'] = bool(self.result_product_ids)
            if staticpage_search_enabled():
                context['staticpages'] = self.get_staticpage_search_queryset()

        if hasattr(self.request, 'seo'):
            self.request.seo.breadcrumbs.append(('', _('Search Results')))

            meta_keywords = self.keywords.replace(',', ' ').split()
            self.request.seo.meta_keywords = ', '.join(meta_keywords)

            meta_description = self.keywords
            if config.SEO_SEARCH_META_DESC_PREFIX:
                meta_description = (
                    f'{config.SEO_SEARCH_META_DESC_PREFIX} {meta_description}'
                )
            if config.SEO_SEARCH_META_DESC_SUFFIX:
                meta_description = (
                    f'{meta_description} {config.SEO_SEARCH_META_DESC_SUFFIX}'
                )
            self.request.seo.meta_description = meta_description

        return context
