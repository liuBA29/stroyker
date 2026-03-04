from django.core.management.base import BaseCommand
from constance.models import Constance


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('config_key', nargs="+", type=str)
        parser.add_argument('config_old_value', nargs="+", type=str)
        parser.add_argument('config_new_value', nargs="+", type=str)

    def handle(self, *args, **options):
        Constance.objects.filter(
            key=options['config_key'],
            value=options['config_old_value']).update(value=options['config_new_value'])
