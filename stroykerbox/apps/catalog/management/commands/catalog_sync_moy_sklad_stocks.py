from logging import getLogger

from django.core.management.base import BaseCommand
from django.utils import timezone

from stroykerbox.apps.catalog.sync.moy_sklad import get_client, MoySkladApiError
from stroykerbox.apps.catalog import models


logger = getLogger('catalog.moy_sklad.sync')


class Command(BaseCommand):
    """ Synchronizes product's stocks with MoySklad system. """

    def handle(self, *args, **options):
        start_datetime = timezone.now()
        log_messages = []

        logger.info('Start stocks synchronization...')
        stocks_updated = stocks_created = failed = 0
        processed_prod_ids = set()

        ms_client = get_client()
        ms_stocks = ms_client.stock.get_stocks_by_store()
        prods_to_sync = models.Product.objects.filter(sku__isnull=False)
        warehouses = models.Stock.objects.filter(
            third_party_code__isnull=False)

        for s in ms_stocks:
            remote_product_id = s['meta']['uuidHref'].split('id=')[1]
            try:
                rp = ms_client.product.get_product(remote_product_id)
            except MoySkladApiError as err:
                msg = f'MoySkladApiError (ID {remote_product_id}): {err}'
                logger.error(msg)
                log_messages.append(msg)
                failed += 1
                continue

            try:
                product = prods_to_sync.get(sku=rp['article'])
            except KeyError:
                msg = f'MoySklad stocks sync error: remote product "article" field is not set. id={rp["id"]}'
                logger.error(msg)
                log_messages.append(msg)
                failed += 1
                continue
            except models.Product.DoesNotExist:
                msg = f'MoySklad stocks sync error: local product with sku={rp["article"]} does not exist.'
                logger.error(msg)
                log_messages.append(msg)
                failed += 1
                continue

            for store in s['stockByStore']:
                store_code = store['meta']['href'].split('/')[-1]
                try:
                    warehouse = warehouses.get(third_party_code=store_code)
                except models.Stock.DoesNotExist:
                    continue
                except models.Stock.MultipleObjectsReturned as e:
                    msg = f'Found several stocks with the same third_party_code {store_code}'
                    log_messages.append(msg)
                    logger.exception(str(e))
                    failed += 1
                    continue

                _, created = models.ProductStockAvailability.objects.update_or_create(
                    product=product,
                    warehouse=warehouse,
                    defaults={'available': int(store['stock'])}
                )
                if created:
                    stocks_created += 1
                else:
                    stocks_updated += 1

                # Collection of a list of products, data about which
                # is in the MoySklad.
                processed_prod_ids.add(product.id)

        # Deleting data on the availability of products,
        # data about which is not available in MoySklad.
        deleted_avail = models.ProductStockAvailability.objects.exclude(
            product_id__in=processed_prod_ids).delete()

        updated_msg = f'Updated stocks: {stocks_updated}'
        created_msg = f'Created stocks: {stocks_created}'
        failed_msg = f'Failed: {failed}'
        deleted_avail_msg = f'Deleted ProductStockAvailability objects: {deleted_avail[0]}'

        logger.info(updated_msg)
        logger.info(created_msg)
        logger.info(failed_msg)
        logger.info(deleted_avail_msg)

        models.MoySkladSyncLog.objects.create(
            operation=models.MOYSKLAD_OPERATION_STOCK_UPDATE,
            start_dt=start_datetime,
            end_dt=timezone.now(),
            log='\n'.join(log_messages),
            summary=f'{updated_msg}\n{created_msg}\n{failed_msg}\n{deleted_avail_msg}'
        )
