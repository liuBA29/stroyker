from django.core.management.base import BaseCommand

from stroykerbox.apps.scraper.models import Scraper
from stroykerbox.apps.scraper.parser import CategoryParser


class Command(BaseCommand):
    help = 'Parse and import product from an external site. '

    def add_arguments(self, parser):
        parser.add_argument('partner', type=str, help='Partner internal slug')
        parser.add_argument('category', type=str, help='Category internal slug')

    def handle(self, *args, **options):
        partner_slug = options.get('partner')
        category_slug = options.get('category')
        if partner_slug and category_slug:
            try:
                scraper = Scraper.objects.get(partner__slug=partner_slug, category__slug=category_slug)
            except Scraper.DoesNotExist:
                self.stdout.write('Scraper does not exist.')
            else:
                self.stdout.write('Start parsing...')
                parser = CategoryParser(scraper)
                parsed_products = parser.parse()
                self.stdout.write('Done.')
                self.stdout.write(f'Parsed products: {parsed_products}')
        else:
            self.stdout.write('Please specify partner and category slugs.')
