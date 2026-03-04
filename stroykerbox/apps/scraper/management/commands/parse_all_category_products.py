from django.core.management.base import BaseCommand

from stroykerbox.apps.scraper.models import Scraper
from stroykerbox.apps.scraper.parser import CategoryParser


class Command(BaseCommand):
    help = 'Parse and import product from an external site. '

    def add_arguments(self, parser):
        parser.add_argument('partner', type=str, help='Partner internal slug')

    def handle(self, *args, **options):
        partner_slug = options.get('partner')
        if partner_slug:
            scrapers = Scraper.objects.filter(partner__slug=partner_slug)
            if scrapers.count() == 0:
                self.stdout.write('There are no any scraper.')
            else:
                for scraper in scrapers:
                    self.stdout.write(f'Start parsing with category {scraper.category.name}...')
                    parser = CategoryParser(scraper)
                    parsed_products = parser.parse()
                    self.stdout.write(f'Parsed {parsed_products} products of category {scraper.category.name}')
                self.stdout.write('Done.')
        else:
            self.stdout.write('Please, specify partner slug.')
