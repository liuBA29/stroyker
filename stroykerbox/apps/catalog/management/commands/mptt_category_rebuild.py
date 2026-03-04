from django.core.management.base import BaseCommand
from django.db import transaction

from stroykerbox.apps.catalog.models import Category


class Command(BaseCommand):
    """
    Rebuild category trees (MPTT).
    """

    def handle(self, *args, **options):
        with transaction.atomic():
            try:
                Category.objects.rebuild()
            except Exception as e:
                self.stderr.write(str(e))
            else:
                self.stdout.write('Дерево категорий успешно перестроено')
