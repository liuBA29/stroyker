from django.core.management.base import BaseCommand
from django.conf import settings

from constance import config
from stroykerbox.apps.catalog.models import ProductImage
from stroykerbox.apps.utils.watermark import create_watermark


class Command(BaseCommand):
    """
    Rebuild category trees (MPTT).
    """

    def handle(self, *args, **options):
        if not all([config.WATERMARK_PRODUCT_IMAGES, config.WATERMARK_FILE]):
            return

        watermarked = 0

        for img in ProductImage.objects.filter(has_watermarked=False):
            if create_watermark(
                    img.image.path, f'{settings.MEDIA_ROOT}/{config.WATERMARK_FILE}'):
                img.has_watermarked = True
                img.save(update_fields=('has_watermarked',))
                watermarked += 1

        return watermarked
