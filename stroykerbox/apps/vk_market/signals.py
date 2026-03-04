from logging import getLogger

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from stroykerbox.apps.catalog.models import Product

from .vk import VKMarket, vk_market_enabled
from .tasks import vk_market_process_product

logger = getLogger(__name__)


@receiver(post_save, sender=Product)
def product_saved(sender, instance, **kwargs):
    """
    В настройках интеграции логика выгрузки:
    1) общий выключатель со значениями - не выгружать / выгружать отмеченные / выгружать все
    2) выгрузка по наличию - выгружать в наличии / выгружать все

    Редактирование товаров:
    - если товар на сайте был изменен, то отправлять в VK методом edit;
    - если стоит настройка "выгружать отмеченные" или "выгружать в наличии" и
        товар перестал быть отмеченным или в наличии,
        то передавать параметр deleted=1;
    """

    if not vk_market_enabled():
        return

    vk_market_process_product.delay(instance.id)


@receiver(pre_delete, sender=Product)
def product_will_be_removed(sender, instance, **kwargs):
    """
    Удаление товаров из VK.
    Если товар удаляется с сайта - отправлять запрос на удаление в VK.
    """
    if hasattr(instance, 'vk_market'):
        VKMarket().delete(instance)
