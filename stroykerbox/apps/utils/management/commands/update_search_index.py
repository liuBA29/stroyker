from django.core.management.base import BaseCommand

from stroykerbox.apps.catalog.models import Product
from stroykerbox.apps.staticpages.models import Page
from stroykerbox.apps.catalog.utils import update_product_search_index
from stroykerbox.apps.staticpages.utils import update_staticpage_search_index


class Command(BaseCommand):
    """
    Update search index base for a products.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--products',
            dest='products',
            action='store_true',
            default=False,
            help='Update search index for a catalog products.'
        )
        parser.add_argument(
            '--staticpages',
            dest='staticpages',
            action='store_true',
            default=False,
            help='Update search index for a staticpages.'
        )

    def handle(self, *args, **options):
        products, staticpages = options.get(
            'products'), options.get('staticpages')
        verbosity = options.get('verbosity', 1)

        update_all = not products and not staticpages
        # update index for a catalog products
        if products or update_all:
            updated = 0
            for p in Product.objects.published():
                if update_product_search_index(p):
                    updated += 1
                    if verbosity:
                        self.stdout.write(self.style.SUCCESS(
                            f'Search base for the product "{p.name}" has been successfully updated.'))
            if verbosity:
                self.stdout.write(self.style.SUCCESS(
                    f'Updated products: {updated}.'))

        if staticpages or update_all:
            # update index for a staticages
            updated = 0
            for p in Page.objects.filter(published=True):
                if update_staticpage_search_index(p):
                    updated += 1
                    if verbosity:
                        self.stdout.write(self.style.SUCCESS(
                            f'Search base for the page "{p.title}" has been successfully updated.'))
            if verbosity:
                self.stdout.write(self.style.SUCCESS(
                    f'Updated staticpages: {updated}.'))
