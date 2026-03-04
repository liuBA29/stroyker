from django.db import models
from django.utils.translation import gettext_lazy as _

from stroykerbox.apps.catalog.models import Category, Parameter, Stock


class SubcategoryAsParameter(models.Model):
    """
    Модель для связи определенной категории каталога товаров с определенным параметром
    товара.
    Используется при получении данных о товаре с сервера SmartLombard. Если
    существует данная модель с указанной родительской категорией, совпадающей с родительской
    категорией синхронизируемого товара, тогда все "приходящие" подкатегории будут рассматриваться,
    при парсинге, как параметр товара.
    """

    parent_category = models.OneToOneField(
        Category, on_delete=models.CASCADE, verbose_name=_('parent category')
    )
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.parent_category.name}:{self.parameter.name}'


class TicketStock(models.Model):
    """
    Модель для сопоставления кодов, зашитых в залоговые билеты, определенным
    филиалам (магазинам/складам).
    """

    stock = models.ForeignKey(
        Stock, on_delete=models.CASCADE, verbose_name=_('lombard_ticket_codes')
    )
    code = models.CharField(_('ticket stock code'), max_length=2, unique=True)

    # https://redmine.fancymedia.ru/issues/12870
    is_closed = models.BooleanField(
        'отделение закрыто',
        default=False,
        help_text=(
            'Включение данной опции будет означать, что магазин с '
            'соответствующим кодом больше не работает.'
        ),
    )
    msg_for_closed = models.TextField(
        'сообщение для закрытого отделения',
        blank=True,
        null=True,
        help_text=(
            'Сообщение, отображаемое пользователю, '
            'когда отделение закрыто. Можно использовать HTML-теги.'
        ),
    )

    class Meta:
        unique_together = (('stock', 'code'),)
        verbose_name = _('ticket stock')
        verbose_name_plural = _('ticket stocks')

    def __str__(self):
        return f'{self.code}:{self.stock.name}'


class UpdateLog(models.Model):
    created = models.DateTimeField(_('created date'), auto_now_add=True)
    log = models.JSONField(_('log data'), default=list, blank=True)

    class Meta:
        ordering = ['-created']
        verbose_name = _('update log')
        verbose_name_plural = _('update logs')

    def __str__(self):
        return f'log for {self.created}'

    def write(self, msg=None, commit=True):
        if not msg:
            return
        self.log.append(msg)
        if commit:
            self.save(update_fields=['log'])


from .tbank.models import *  # noqa
