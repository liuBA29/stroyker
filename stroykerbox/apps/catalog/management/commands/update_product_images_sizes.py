from django.core.management.base import BaseCommand

from stroykerbox.apps.catalog.models import ProductImage


class Command(BaseCommand):
    """
    Обновление данных о размера изображений товаров (модель ProductImage)
    """

    def handle(self, *args, **options):
        for i in ProductImage.objects.all():
            i.update_file_size_value()
