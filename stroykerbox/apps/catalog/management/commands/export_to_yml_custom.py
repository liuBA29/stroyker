import os
from logging import getLogger

from django.conf import settings
from django.db.models import Q, QuerySet
from constance import config

from stroykerbox.apps.catalog.models import Product, YmlCustomExport
from .export_to_yml import Command as BaseCommand

logger = getLogger('yml_export')


class Command(BaseCommand):
    help = 'Products export to YML'

    def add_arguments(self, parser):
        parser.add_argument(
            '-s',
            '--slug',
            action='store',
            type=str,
            dest='slug',
            help='slug of yml export',
        ),

    def _get_products(self, **options) -> QuerySet[Product]:
        qs = None
        yml_export = options['yml_export']
        if yml_export.type == YmlCustomExport.CATEGORY:
            qs = Product.objects.filter(
                categories__in=self.get_categories(**options)
            ).distinct()
        elif yml_export.type == YmlCustomExport.PRODUCT:
            pks = yml_export.ymlcustomproductexport_set.values_list(
                'product_id', flat=True
            )
            qs = Product.objects.filter(pk__in=pks).distinct()
        else:
            raise NotImplementedError

        # https://redmine.nastroyker.ru/issues/16143
        if (
            qs
            and not config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE
            and config.YML_EXCLUDE_NOT_AVAIL
        ):
            qs = qs.exclude(
                Q(stocks_availability__available__isnull=True)
                | Q(stocks_availability__available__lte=0)
            )
        return qs or Product.objects.none()

    def get_file_path(self, **options):
        return os.path.join(
            settings.YML_EXPORT_CATALOG, f"{options['yml_export'].slug}.yml"
        )

    def get_categories(self, **options):
        yml_export = options['yml_export']
        if yml_export.type == yml_export.CATEGORY:
            categories = []
            for category in yml_export.categories.all():
                categories.append(category)
                categories.extend(category.get_descendants())
            categories.sort(key=lambda x: x.pk)
            return categories
        return super().get_categories(**options)

    def handle(self, *args, **options):
        options['yml_export'] = YmlCustomExport.objects.get(slug=options['slug'])
        super().handle(*args, **options)
