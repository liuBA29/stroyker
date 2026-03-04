from logging import getLogger

from django.core.management import call_command
from django.conf import settings

from django_rq import job
from constance import config
from stroykerbox.apps.utils.watermark import create_watermark

from stroykerbox.apps.catalog.models import YmlCustomExport

from .utils import update_product_search_index
from .models import ProductImage


@job
def search_index_updater(instance):
    update_product_search_index(instance)


@job('default', timeout=1800)
def sync_moy_sklad_prices():
    logger = getLogger('catalog.moy_sklad.sync')
    if getattr(config, 'SYNC_PRICES_ENABLED', None):
        logger.debug('Starting price synchronization with the MoySklad server.')
        call_command('catalog_sync_moy_sklad_prices')
    else:
        logger.debug(
            'Synchronization of prices with the MoySklad server is disabled by settings. '
            'Canceling the task.'
        )


@job('default', timeout=1800)
def sync_moy_sklad_stocks():
    logger = getLogger('catalog.moy_sklad.sync')
    if config.SYNC_STOCKS_ENABLED:
        logger.debug('Starting stocks synchronization with the MoySklad server.')
        call_command('catalog_sync_moy_sklad_stocks')
    else:
        logger.debug(
            'Synchronization of stocks with the MoySklad server is disabled by settings. '
            'Canceling the task.'
        )


@job
def watemark_product_image(instance_id):
    if not config.WATERMARK_FILE:
        return 'The watermark file is not set.'

    try:
        instance = ProductImage.objects.get(id=instance_id, has_watermarked=False)
    except ProductImage.DoesNotExist:
        return f'Product Image object with ID {instance_id} not found or already watermarked.'

    watermark = create_watermark(
        instance.image.path,
        f'{settings.MEDIA_ROOT}/{config.WATERMARK_FILE}',
    )

    if watermark:
        instance.has_watermarked = True
        instance.save(update_fields=('has_watermarked',))
        return f'Image {watermark} for product {instance.product.name} has been watermarked.'


@job('default', timeout=1800)
def update_yml_file():
    logger = getLogger('yml_export')
    if config.YML_UPDATE_INTERVAL and config.YML_UPDATE_INTERVAL != '0':
        logger.debug('Starting for update YML file.')
        call_command('export_to_yml')


@job('default', timeout=1800)
def update_custom_yml_file():
    logger = getLogger('yml_export')
    if config.YML_UPDATE_INTERVAL and config.YML_UPDATE_INTERVAL != '0':
        for yml_export in YmlCustomExport.objects.all():
            logger.debug(f'Starting for update {yml_export.slug}.yml file.')
            call_command('export_to_yml_custom', slug=yml_export.slug)
