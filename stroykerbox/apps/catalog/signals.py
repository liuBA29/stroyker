import sys
import importlib

from django.core.management import call_command
from django.db import transaction
from django.db.models.signals import post_save, pre_save, pre_delete, post_delete
from django.dispatch import receiver
from django.conf import settings
from constance.signals import config_updated

from uuslug import uuslug
from constance import config

from .tasks import search_index_updater, watemark_product_image
from .models import (Product, ProductLocationPrice,
                     ProductPriceHistory, Category, ProductImage, Currency)
from .utils import clear_categories_menu_template_cache


@receiver(pre_save, sender=Product)
def check_and_set_product_slug(sender, instance, *args, **kwargs):
    """
    If a slug is not specified for the product, it generates it from the product name.
    """
    if not instance.slug:
        instance.slug = uuslug(instance.name, instance=instance)


@receiver(post_save, sender=Product)
def product_save_price_post_save_callback(sender, instance, **kwargs):
    """
    When the product is updated and its price is changed, an object is created
    to store the previous value of the product price.
    """
    qs_price = ProductPriceHistory.objects.filter(product=instance)
    if instance.price and (not qs_price.exists() or (instance.price != qs_price.last().price)):
        ProductPriceHistory.objects.update_or_create(
            product=instance,
            location__isnull=True,
            created__day=instance.updated_at.day,
            created__month=instance.updated_at.month,
            created__year=instance.updated_at.year,
            defaults={'price': instance.price}
        )

    # The search index update will only be runned for products displayed on the site.
    if instance.published and config.SEARCH__USE_FULLTEXT:
        transaction.on_commit(
            lambda: search_index_updater.delay(instance))


@receiver(post_save, sender=ProductLocationPrice)
def product_location_price_post_save_callback(sender, instance, **kwargs):
    """
    When the product price for some location is updated,
    an object is created to store the previous value of the product price.
    """
    qs_price = ProductPriceHistory.objects.filter(product=instance.product)
    if instance.price and (not qs_price.exists() or (instance.price != qs_price.last().price)):
        kwargs = {'product': instance.product,
                  'created__day': instance.updated_at.day,
                  'created__month': instance.updated_at.month,
                  'created__year': instance.updated_at.year,
                  'defaults': {'price': instance.price}
                  }
        if instance.location:
            kwargs['location'] = instance.location
        else:
            kwargs['location__isnull'] = True
        ProductPriceHistory.objects.update_or_create(**kwargs)


@receiver(post_delete, sender=Category)
@receiver(post_save, sender=Category)
def on_save_del_catalog_category(sender, instance, **kwargs):
    clear_categories_menu_template_cache()


@receiver(pre_delete, sender=Category)
def reset_subcategories_level(sender, instance, **kwargs):
    Category.objects.filter(parent=instance).update(level=0)


@receiver(config_updated)
def constance_updated(sender, key, old_value, new_value, **kwargs):
    if ((old_value == '' and new_value is None) or (old_value == new_value)):
        return

    KEYS_FOR_CACHE_CLEAN = ('CATALOG_MENU_TITLE',)

    if (key == 'YML_URL' and settings.ROOT_URLCONF in sys.modules):
        importlib.reload(sys.modules[settings.ROOT_URLCONF])

    if key in ('YML_UPDATE_INTERVAL', 'SYNC_PRICES_PERIOD', 'SYNC_STOCKS_PERIOD'):
        call_command('catalog_sync_scheduler')

    # очищаем кэш при обновлении определенных настроек
    if key in KEYS_FOR_CACHE_CLEAN:
        call_command('clearcache')


@receiver(post_save, sender=ProductImage)
def new_product_image_created(sender, instance, created, **kwargs):
    if all([created, config.WATERMARK_PRODUCT_IMAGES, config.WATERMARK_FILE]):
        watemark_product_image.delay(instance.id)


@receiver(post_save, sender=Currency)
def delete_multiply_default_currency(sender, instance, **kwargs):
    if instance.is_default:
        Currency.objects.filter(is_default=True).exclude(
            pk=instance.pk).update(is_default=False)
