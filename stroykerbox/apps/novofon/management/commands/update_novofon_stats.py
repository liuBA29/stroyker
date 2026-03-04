from django.core.management.base import BaseCommand

from stroykerbox.apps.novofon.helper import Novofon


class Command(BaseCommand):
    def handle(self, *args, **options):
        Novofon().process_stats()
