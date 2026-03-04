from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone


class B24Log(models.Model):
    lead_id = models.PositiveIntegerField('id на стороне b24')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    data = models.JSONField('данные ответа от b24', default=dict)

    def __str__(self):
        return str(self.lead_id)

    class Meta:
        ordering = ('-lead_id',)
        verbose_name = 'запрос на создание объекта B24'
        verbose_name_plural = 'запросы на создание объектов B24'

    def write_to_log(self, data, save=True):
        if not isinstance(self.data, dict):
            self.data = {}
        self.data.update({f'{timezone.now()}': data})
        if save:
            self.save(update_fields=('data',))
