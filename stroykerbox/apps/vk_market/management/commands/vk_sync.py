from logging import getLogger
import time
from json.decoder import JSONDecodeError

from django.core.management.base import BaseCommand
from django.db.models import Q
from constance import config

from stroykerbox.apps.catalog.models import Product
from stroykerbox.apps.vk_market.vk import VKMarket, vk_market_enabled
from stroykerbox.apps.vk_market import conf as vk_conf


logger = getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('product_ids', nargs='*', type=int)

    def get_product_ids_list(self):
        qs = Product.objects.all()

        # https://redmine.fancymedia.ru/issues/12553
        if config.VK_MARKET_UNLOAD_VARIANT == vk_conf.UNLOAD_VARIANT_CHECKED:
            qs = qs.filter(Q(vk_product__isnull=False) | Q(vk_market=True))
        if config.VK_MARKET_AVAIL_ONLY:
            qs = qs.filter(
                Q(vk_product__isnull=False) | Q(
                    stocks_availability__available__gt=0)
            ).distinct()

        return qs.values_list('id', flat=True)

    def _check_for_new_vk_product(self, product):
        return bool(
            (
                config.VK_MARKET_UNLOAD_VARIANT == vk_conf.UNLOAD_VARIANT_ALL or
                (
                    config.VK_MARKET_UNLOAD_VARIANT == vk_conf.UNLOAD_VARIANT_CHECKED and
                    product.vk_market
                )
            ) and
            (
                not config.VK_MARKET_AVAIL_ONLY or
                (config.VK_MARKET_AVAIL_ONLY and product.is_available())
            )
        )

    def proccess_product(self, product_id):
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            self.errors.append(f'Товар с ID {product_id} не найден.')
            return
        except Exception as e:
            self.errors.append(str(e))
            return

        is_new = not hasattr(product, 'vk_product')

        if is_new and not self._check_for_new_vk_product(product):
            return

        categories_qs = product.categories.filter(
            vk_group_id__isnull=False).exclude(vk_group_id=0)

        if (not categories_qs.exists()):
            msg = (f'У товара {product} не найдено категорий, '
                   'сопоставленных с категориями на VK-Маркете.')
            logger.error(msg)
            self.errors.append(msg)
            return

        if not product.images.exists():
            msg = (
                f'У товара {product} не найдено ни одного фото для VK-Маркета.')
            logger.error(msg)
            self.errors.append(msg)
            return

        try:
            result_ok = None
            if is_new:
                result_ok = self.vk.add(product)
            else:
                result_ok = self.vk.edit(product)

            if result_ok:
                return True
        except JSONDecodeError as js_e:
            self.errors.append('Ошибка при декодировки из json (JSONDecodeError).\n'
                               f'Данные по переменным: "is_new" - {is_new}, "product" - {product}')
            logger.exception(js_e)
        except Exception as e:
            self.errors.append(str(e))
            logger.exception(e)

    def handle(self, *args, **options):
        self.messages = []
        self.errors = []

        verbosity = (options.get('verbosity', 0) > 0)

        if not vk_market_enabled():
            msg = ('VK-Маркет отключен или в настройках не указаны все '
                   'необходимые для синхронизации параметры.')
            if verbosity:
                return msg
            else:
                logger.info(msg)
            return

        self.vk = VKMarket()

        product_ids = options['product_ids'] or self.get_product_ids_list()

        if not product_ids:
            self.errors.append('No matching products were found to sync.')
        else:
            for product_id in product_ids:
                if self.proccess_product(product_id):
                    self.messages.append(
                        f'Товар с ID: {product_id} успешно синхронизирован.')
                else:
                    self.errors.append(
                        f'Ошибка синхронизации товара с ID: {product_id}')
                timeout = int(config.VK_MAKET_SYNC_TIMOUT_SEC)
                if timeout:
                    time.sleep(timeout)

        logger.info(self.messages)

        if self.errors:
            logger.error(self.errors)

        if verbosity:
            messages = '\n'.join(self.messages)
            errors = '\n'.join(self.errors)
            return f'{messages}\n\n{errors}'
