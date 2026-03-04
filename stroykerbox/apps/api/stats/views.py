from datetime import date, timedelta

from constance.models import Constance
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models.functions import Trunc
from django.db.models import Count, Sum, DateField, Case, When, Q, F
from django.contrib.sites.shortcuts import get_current_site
from django.urls import resolve
from django.conf import settings

from stroykerbox.apps.commerce.models import Order, OrderProductMembership
from stroykerbox.apps.banners.models import Banner
from stroykerbox.apps.crm.models import CrmRequestBase, CRM_REQUEST_NEW
from stroykerbox.apps.api.permissions import AllowedKey, AllowedIP
from stroykerbox.apps.catalog.models import Product, ProductPriceHistory
from stroykerbox.apps.custom_forms.models import CustomFormResult
from stroykerbox.apps.news.models import News
from stroykerbox.apps.common.services.checker import CommonChecker

from stroykerbox import __version__, get_commits_count

from .serializers import ProductInfoSerializer


from .serializers import (
    OrderStatsSerializer,
    CartAmountStatsSerializer,
    CartTopProductsStatsSerializer,
    BannerSerializer,
    CrmRequestSerializer,
    CustomFormSerializer,
)


class StatsInfoBase(APIView):
    permission_classes = [AllowedKey | AllowedIP]


class StatsInfo(StatsInfoBase):

    def get(self, request, format=None):
        return Response(
            {
                'stroyker_version': 'k1',
            }
        )


class NewsUpdatesInfo(StatsInfoBase):
    def get(self, request, format=None):
        prev_month_date = date.today() - timedelta(days=30)

        return Response(
            {
                'updates_for_last_month': News.objects.filter(
                    updated_at__year=prev_month_date.year,
                    updated_at__month=prev_month_date.month,
                ).count(),
            }
        )


class PriceHistoryInfo(StatsInfoBase):

    def get(self, request, format=None):
        prev_month_date = date.today() - timedelta(days=30)

        return Response(
            {
                'updates_for_last_month': ProductPriceHistory.objects.filter(
                    created__year=prev_month_date.year,
                    created__month=prev_month_date.month,
                ).count(),
            }
        )


class VersionInfo(StatsInfoBase):

    def get(self, request, format=None):
        return Response(
            {
                'current_version': __version__,
                'commits_for_last_month': get_commits_count(),
            }
        )


class StatsViewBase(StatsInfoBase):

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.view_mode = 'day' if request.GET.get('by_day') else 'month'
        self.start_date, self.end_date = request.GET.get('start_date'), request.GET.get(
            'end_date'
        )


class CartOrderStatsView(StatsViewBase):

    def get(self, request, format=None):
        orders = Order.objects.all()

        if self.start_date and self.end_date:
            orders = orders.filter(created_at__range=[self.start_date, self.end_date])

        orders = (
            orders.annotate(
                date=Trunc('created_at', self.view_mode, output_field=DateField())
            )
            .values('date')
            .annotate(total=Count('id'))
            .order_by('date')
        )

        serializer = OrderStatsSerializer(orders, many=True)
        return Response(serializer.data)


class CartAmountStatsView(StatsViewBase):

    def get(self, request, format=None):
        amounts = Order.objects.all().exclude(status='draft')

        if self.start_date and self.end_date:
            amounts = amounts.filter(created_at__range=[self.start_date, self.end_date])

        amounts = (
            amounts.annotate(
                date=Trunc('created_at', self.view_mode, output_field=DateField())
            )
            .values('date')
            .annotate(amount_rub=Sum('final_price'))
            .order_by('date')
        )

        serializer = CartAmountStatsSerializer(amounts, many=True)
        return Response(serializer.data)


class CartTopProductsStatsView(StatsViewBase):

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.limit = request.GET.get('limit', 20)

    def get(self, request, format=None):
        products = OrderProductMembership.objects.all()

        if self.start_date and self.end_date:
            products = products.filter(
                order__created_at__range=[self.start_date, self.end_date]
            )

        products = (
            products.values('product__name', 'product__sku')
            .annotate(total=Count('product_id'))
            .order_by('-total')
        )

        serializer = CartTopProductsStatsSerializer(products[: self.limit], many=True)
        return Response(serializer.data)


class BannerStatsView(StatsInfoBase):

    def get(self, request, format=None):
        banners = Banner.objects.all()
        serializer = BannerSerializer(banners, many=True, context={'request': request})
        return Response(serializer.data)


class CrmStatsView(StatsViewBase):

    def get(self, request, format=None, object_class=None):
        crm_orders = CrmRequestBase.objects.all()
        if self.start_date and self.end_date:
            crm_orders = crm_orders.filter(
                created__range=[self.start_date, self.end_date]
            )

        if object_class:
            crm_orders = crm_orders.filter(object_class=object_class)

        crm_orders = (
            crm_orders.annotate(
                date=Trunc('created', self.view_mode, output_field=DateField()),
            )
            .values('date', 'object_class')
            .annotate(
                total=Count('id'),
                total_processed=Count(
                    Case(
                        When(~Q(status=CRM_REQUEST_NEW), then=1),
                    )
                ),
            )
            .order_by('date')
        )

        serializer = CrmRequestSerializer(crm_orders, many=True)
        return Response(serializer.data)


class SocialInfoView(StatsViewBase):
    CONF_SOCIAL_PREFIX = 'SOCIAL_LINK_'

    def get(self, request, format=None, service=None):
        qs = Constance.objects.filter(key__istartswith=self.CONF_SOCIAL_PREFIX).values(
            'key', 'value'
        )
        if service:
            qs = qs.filter(key__iendswith=service)
        data = {
            s['key'].replace(self.CONF_SOCIAL_PREFIX, '').lower(): s['value']
            for s in qs.values()
            if s['value'].startswith('http')
        }
        return Response(data)


class ProductInfoByPath(StatsViewBase):
    def get_object(self):
        view = resolve(self.local_path)
        product_slug = view.kwargs.get('product_slug')
        try:
            return Product.objects.get(slug=product_slug)
        except Product.DoesNotExist:
            pass

    def prepare_path(self, product_path):
        site = get_current_site(self.request)
        base_url = settings.BASE_URL
        if site.domain in base_url:
            domain = site.domain
        else:
            domain = base_url.split('//')[-1]

        local_path = product_path.split(domain)[-1]
        if not local_path.startswith('/'):
            local_path = f'/{local_path}'
        self.local_path = local_path

    def get(self, request, product_path):
        self.prepare_path(product_path)
        obj = self.get_object()
        if obj:
            data = ProductInfoSerializer(obj).data
        else:
            data = dict(error='Product not found')

        return Response(data)


class CustomFormStatsView(StatsViewBase):

    def get(self, request, format=None, form_key=None):
        form_results = CustomFormResult.objects.all()
        if self.start_date and self.end_date:
            form_results = form_results.filter(
                created__range=[self.start_date, self.end_date]
            )

        if form_key:
            form_results = form_results.filter(form__key=form_key)

        form_results = (
            form_results.annotate(
                date=Trunc('created', self.view_mode, output_field=DateField()),
            )
            .values('date', 'form')
            .annotate(
                total=Count('id'),
                form_name=F('form__title'),
            )
            .order_by('date')
        )

        serializer = CustomFormSerializer(form_results, many=True)
        return Response(serializer.data)


class ActiveProductCount(StatsInfoBase):
    def get(self, request):
        """
        Возвращаем общее кол-во опубликованных товаров.
        """
        qs = Product.objects.all()
        return Response(
            {'result': qs.filter(published=True).count(), 'total': qs.count()}
        )


class ContentQualityValue(StatsInfoBase):
    def get(self, request) -> Response:
        """
        Общая оценка наполнения сайта (проекта).
        https://redmine.nastroyker.ru/issues/16858
        """
        value = CommonChecker().calculate_summary_point()
        return Response({'value': value})


class ContentQualityValueProduct(StatsInfoBase):
    def get(self, request) -> Response:
        """
        Общая оценка наполнения сайта (проекта).
        https://redmine.nastroyker.ru/issues/16858
        """
        value = CommonChecker().calculate_product_points
        return Response({'value': value})
