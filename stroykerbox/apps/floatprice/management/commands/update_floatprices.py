from logging import getLogger
from random import randint

from django.core.management.base import BaseCommand
from constance import config

from stroykerbox.apps.catalog.models import Product
from stroykerbox.apps.floatprice.models import FloatPrice

logger = getLogger(__name__)


class Command(BaseCommand):
    """
    Обновление "плавающих цен" товаров.

    Последние изменения в логике процесса согласно описанному в задачe:
        https://redmine.fancymedia.ru/issues/10528
    """

    def handle(self, *args, **options):
        if not config.FLOATPRICE_IS_ACTIVE:
            # https://redmine.nastroyker.ru/issues/14970
            deleted, __ = FloatPrice.objects.all().delete()
            msg = f'Удалено объектов "плавающих цен": {deleted}'
            if options.get('verbosity'):
                self.stdout.write(self.style.SUCCESS(msg))
            else:
                logger.info(msg)
            return
        elif config.FLOATPRICE_PERCENT <= 0:
            return

        updated = new = 0

        for obj in Product.objects.filter(price__isnull=False).exclude(price=0):
            if getattr(obj, 'floatprice', None) and obj.floatprice.percent:
                float_percent = obj.floatprice.percent
            else:
                float_percent = config.FLOATPRICE_PERCENT

            if float_percent:
                float_sum = (obj.price / 100) * float_percent
                float_price = randint(
                    int(obj.price - float_sum), int(obj.price + float_sum)
                )
            else:
                float_price = obj.price

            __, created = FloatPrice.objects.update_or_create(
                product=obj, defaults={'price': float_price}
            )
            if created:
                new += 1
            else:
                updated += 1

        msg = f'Обновлено: {updated}\nСоздано новых: {new}'

        if options.get('verbosity'):
            self.stdout.write(self.style.SUCCESS(msg))
        else:
            logger.info(msg)
