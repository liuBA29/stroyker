from django.utils.functional import cached_property
from django.db import models
from django.utils.translation import ugettext as _

from stroykerbox.apps.catalog.models import Product


class FloatPrice(models.Model):
    product = models.OneToOneField(Product, primary_key=True, related_name='floatprice',
                                   on_delete=models.CASCADE, editable=False)
    price = models.DecimalField(_('плавающая цена'), max_digits=12, decimal_places=2,
                                help_text=_('Плавающая цена, которая будет заменять основную цену товара.'))
    percent = models.PositiveSmallIntegerField(
        _('процент'), null=True, blank=True,
        help_text=_('Собственный процент для формирования плавающей цены конкретного товара. '
                    'Если не установлен - используется процент из глобальных настроек.'))
    created_at = models.DateTimeField(_('дата/время создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('дата/время обновления'), auto_now=True)

    @cached_property
    def currency_price(self):
        return self.price * self.product.currency_rate

    @cached_property
    def currency_old_price(self):
        return self.currency_price

    @cached_property
    def currency_purchase_price(self):
        return self.currency_price

    def __str__(self):
        if self.pk:
            return str(self.product)
        return ''

    class Meta:
        verbose_name = _('плавающая цена товара')
        verbose_name_plural = _('плавающие цены товара')
        ordering = ('-updated_at',)

    @property
    def purchase_price(self):
        return self.price

    @property
    def old_price(self):
        return self.price
