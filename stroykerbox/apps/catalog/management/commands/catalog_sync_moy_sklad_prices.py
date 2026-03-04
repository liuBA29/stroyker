from decimal import Decimal
from logging import getLogger

from django.core.management.base import BaseCommand
from django.db import Error
from django.db.transaction import atomic
from django.utils import timezone

from constance import config
from stroykerbox.apps.catalog.sync.moy_sklad import get_client
from stroykerbox.apps.catalog.models import (
    Product,
    MoySkladSyncLog,
    MOYSKLAD_OPERATION_PRICE_UPDATE,
)


logger = getLogger('catalog.moy_sklad.sync')


class Command(BaseCommand):
    """Synchronizes product's prices with MoySklad system."""

    def handle(self, *args, **options):
        start_datetime = timezone.now()
        log_messages = []
        summary = ''
        failed = 0

        logger.info('Start prices synchronization...')
        prods_to_save = set()
        ms_client = get_client()
        ms_products = ms_client.product.get_products()
        prods_to_sync = Product.objects.filter(sku__isnull=False, published=True)
        for p in ms_products:

            try:
                product = prods_to_sync.get(sku=p['article'])
            except KeyError:
                msg = f'MoySklad prices sync error: remote product "article" field is not set. id={p["id"]}'
                logger.error(msg)
                log_messages.append(msg)
                failed += 1
                continue
            except Product.DoesNotExist:
                msg = f'MoySklad prices sync error: local product with sku={p["article"]} does not exist.'
                logger.error(msg)
                log_messages.append(msg)
                failed += 1
                continue

            try:
                for prices in p.get('salePrices', []):
                    price_type_name = prices.get('priceType', {}).get('name')
                    if price_type_name == config.SYNC_PRICE_FIELDNAME:
                        # from kopeiki to rubles
                        product.price = Decimal(prices['value']) / 100
                    elif config.SYNC_OLD_PRICE_FIELDNAME and (
                        price_type_name == config.SYNC_OLD_PRICE_FIELDNAME
                    ):
                        product.old_price = Decimal(prices['value']) / 100

                # https://redmine.fancymedia.ru/issues/13273#note-2
                if buy_price := p.get('buyPrice', {}).get('value'):
                    product.purchase_price = (
                        Decimal(buy_price) / 100
                    )  # from kopeiki to rubles

                if not product.price and product.old_price:
                    product.price, product.old_price = product.old_price, product.price
                prods_to_save.add(product)
            except Exception as e:
                logger.error(e)
                failed += 1
                continue

        len_product_set = len(prods_to_save)
        if len_product_set > 0:
            self.bulk_save(prods_to_save)
            summary = f'Updated prices of {len_product_set} product(s).'
            logger.info(summary)
        else:
            summary = 'No products to update (you need to specify "article" field of target products).'
            logger.info(summary)

        MoySkladSyncLog.objects.create(
            operation=MOYSKLAD_OPERATION_PRICE_UPDATE,
            start_dt=start_datetime,
            end_dt=timezone.now(),
            log='\n'.join(log_messages),
            summary=f'{summary}\nFailed: {failed}',
        )

    @atomic
    def bulk_save(self, products):
        for product in products:
            try:
                product.save()
            except (ValueError, Error) as e:
                logger.exception(e)
