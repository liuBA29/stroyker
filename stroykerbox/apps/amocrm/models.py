from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomFormFieldAMO(models.Model):
    field_object = models.OneToOneField(
        'custom_forms.CustomFormField', verbose_name=_('поле кастомной формы'),
        primary_key=True, on_delete=models.CASCADE,
        related_name='amocrm')
    amo_id = models.PositiveIntegerField(_('ID поля в AMO CRM'))

    class Meta:
        verbose_name = _('id поля в amocrm')
        verbose_name_plural = _('id полей в amocrm')

    def __str__(self):
        return self.field_object.label
