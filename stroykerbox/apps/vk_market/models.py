from django.db import models
from django.utils.translation import ugettext_lazy as _

from stroykerbox.apps.catalog import models as catalog_models


class VKProductMembership(models.Model):
    product = models.OneToOneField(
        catalog_models.Product, primary_key=True, related_name='vk_product',
        on_delete=models.CASCADE, editable=False)
    vk_id = models.CharField(_('vk id'), max_length=32, editable=False)

    class Meta:
        verbose_name = _('связь товар/vk-товар')
        verbose_name_plural = _('связи товар/vk-товар')

    def __str__(self):
        return self.product.name


class VKCategory(models.Model):
    id = models.PositiveIntegerField(primary_key=True, editable=False)
    name = models.CharField(_('название'), max_length=255)
    section_id = models.PositiveIntegerField(_('ID раздела'), default=0)
    section_name = models.CharField(_('название раздела'), max_length=255)

    class Meta:
        ordering = ('name', )
        verbose_name = _('категория vk-товара')
        verbose_name_plural = _('категории vk-товаров')

    def __str__(self):
        return self.name
