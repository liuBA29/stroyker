from typing import Optional

from django.db import models
from django.utils import timezone

from .services.tbank_api import TBankAPI


class TBankPayment(models.Model):
    payment_id = models.CharField(
        'Payment ID',
        max_length=32,
        primary_key=True,
        help_text=('Назначается на стороне Т-Банка при инициализации платежа.'),
    )
    order_id = models.CharField(
        'Order ID',
        max_length=32,
        help_text=(
            'Номер(идентификатор) заказа на стороне сайта. Например при оплате залогового билета, '
            'этим номером будет номер билета.'
        ),
    )
    amount = models.PositiveIntegerField('сумма в копейках')
    created_at = models.DateTimeField(
        'дата/время создания', auto_now_add=True, editable=False
    )
    payment_url = models.URLField('url формы оплаты')
    status = models.CharField('текущий статус', max_length=16, default='NEW')

    log = models.JSONField('логи проверки статуса', default=dict, blank=True)

    def write_to_log(self, data, save=True):
        if not isinstance(self.log, dict):
            self.log = {}
        self.log.update({f'{timezone.now()}': data})
        if save:
            self.save(update_fields=('log',))

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'платеж через т-банк'
        verbose_name_plural = 'платежи через т-банк'

    def __str__(self):
        return f'{self.payment_id}:{self.order_id}:{self.created_at}'

    @property
    def payment_url_qr(self):
        return TBankAPI.get_qr(self.payment_url) or ''

    def update_payment_status(self, data_dict: Optional[dict] = None) -> bool:
        if data_dict:
            data = data_dict
        else:
            data = TBankAPI().get_payment_status(self.payment_id)

        if not data:
            return False

        self.write_to_log(data, False)
        updated_fields = ['log']
        if 'Status' in data and data['Status'] != self.status:
            updated_fields.append('status')
            self.status = data['Status']
        self.save(update_fields=updated_fields)
        return True
