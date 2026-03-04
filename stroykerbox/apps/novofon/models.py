from django.db import models
from django.utils.translation import ugettext as _


DISPOSITION_CHOICES = {
    'answered': _('разговор'),
    'busy': _('занято'),
    'cancel': _('отменен'),
    'no answer': _('без ответа'),
    'call failed': _('не удался'),
    'no money': _('нет средств, превышен лимит'),
    'unallocated number': _('номер не существует'),
    'no limit': _('превышен лимит'),
    'no day limit': _('превышен дневной лимит'),
    'line limit': _('превышен лимит линий'),
    'no money, no limit': _('превышен лимит')
}

CALL_TYPE_OUTGOING, CALL_TYPE_INCOMING = ('outgoing', 'incoming')
CALL_TYPE_CHOICES = (
    (CALL_TYPE_OUTGOING, _('исходящий')),
    (CALL_TYPE_INCOMING, _('входящий')),
)


class NovofonCall(models.Model):
    id = models.CharField(max_length=64, primary_key=True,
                          help_text=_('Совпадает с ID Новофона.'))
    call_dt = models.DateTimeField(_('дата/время звонка'))
    sip = models.CharField(max_length=16, null=True, blank=True)
    number_from = models.CharField(
        _('from'), max_length=16, help_text=_('С какого номера звонили.'))
    number_to = models.CharField(
        _('to'), max_length=16, help_text=_('Куда звонили.'))
    disposition = models.CharField(_('состояние звонка'), max_length=24)
    billseconds = models.PositiveIntegerField(_('количество секунд звонка'))
    call_type = models.CharField(
        _('тип звонка'), max_length=11, choices=CALL_TYPE_CHOICES, null=True, blank=True)

    class Meta:
        ordering = ('-call_dt',)
        verbose_name = _('звонок через Новофон')
        verbose_name_plural = _('звонки через Новофон')

    def __str__(self):
        return f'{self.id}:{self.call_dt}'
