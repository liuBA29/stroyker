import os
import random

from django.core import management
from django.core.management.base import BaseCommand
from stroykerbox.apps import catalog, commerce
from stroykerbox.apps.catalog import models


class Command(BaseCommand):
    help = 'Import test catalog data (objects from redprice.ru)'

    fixtures_dir = os.path.join(
        os.path.dirname(catalog.__file__), 'fixtures')
    category_fixtures = os.path.join(
        fixtures_dir, 'categories.json')
    product_fixtures = os.path.join(
        fixtures_dir, 'products.json')
    stocks_fixtures = os.path.join(
        fixtures_dir, 'stocks.json')
    product_images_fixtures = os.path.join(
        fixtures_dir, 'product_images.json')

    commerce_fixtures_dir = os.path.join(
        os.path.dirname(commerce.__file__), 'fixtures')
    delivery_cars_fixtures = os.path.join(
        commerce_fixtures_dir, 'delivery_cars.json')

    def create_categories(self):
        management.call_command('loaddata', self.category_fixtures)
        self.stdout.write(self.style.SUCCESS(
            'Categories has been created from %s' % self.category_fixtures))

    def create_products(self):
        management.call_command('loaddata', self.product_fixtures)
        self.stdout.write(self.style.SUCCESS(
            'Products has been created from %s' % self.product_fixtures))

    def create_product_images(self):
        management.call_command('loaddata', self.product_images_fixtures)
        self.stdout.write(self.style.SUCCESS(
            'Product Images has been created from %s' % self.product_images_fixtures))

    def create_related_products(self):
        products_idx = models.Product.objects.all().values_list('id', flat=True)
        for index in products_idx:
            related = random.choice(products_idx)
            if related is index:
                related += 1
            models.ProductRelated.objects.create(
                product_id=related,
                ref_id=index,
            )
        self.stdout.write(self.style.SUCCESS(
            'Related Products has been created'))

    def unpublish_empty_categories(self):
        models.Category.objects.filter(
            level__gt=0, products__isnull=True).update(published=False)
        self.stdout.write(self.style.SUCCESS(
            'Empty Categories has been deleted'))

    def create_stocks(self):
        management.call_command('loaddata', self.stocks_fixtures)
        self.stdout.write(self.style.SUCCESS(
            'Stocks has been created from %s' % self.stocks_fixtures))

    def set_availability_for_products(self):
        stocks_idx = models.Stock.objects.all().values_list('id', flat=True)
        productx_idx = models.Product.objects.all().values_list('id', flat=True)
        for id in productx_idx:
            models.ProductStockAvailability.objects.create(
                warehouse_id=random.choice(stocks_idx),
                product_id=id,
                available=random.randint(0, 2397)
            )
        self.stdout.write(self.style.SUCCESS(
            'The availability value for the products has been set.'))

    def create_delivery_cars(self):
        management.call_command('loaddata', self.delivery_cars_fixtures)
        self.stdout.write(self.style.SUCCESS(
            'Delivery Cars has been created from %s' % self.delivery_cars_fixtures))

    def handle(self, *args, **options):

        self.create_categories()
        self.create_stocks()
        self.create_products()
        self.set_availability_for_products()
        # self.unpublish_empty_categories()
        self.create_related_products()
        self.create_product_images()
        self.create_delivery_cars()
