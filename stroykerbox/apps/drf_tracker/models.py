from datetime import datetime
from django.db import models
from django.conf import settings


class APIRequestLog(models.Model):
    """
    Logs to DB for Django rest framework (drf) API requests
    https://redmine.nastroyker.ru/issues/17343
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    requested_at = models.DateTimeField('дата/время запроса', default=datetime.now)
    response_ms = models.PositiveIntegerField(default=0)
    path = models.CharField(
        'URL запроса',
        max_length=256,
    )
    view = models.CharField(
        max_length=128,
        null=True,
        blank=True,
    )
    view_method = models.CharField(
        max_length=128,
        null=True,
        blank=True,
    )

    data = models.JSONField('данные запроса', default=dict, blank=True)
    response = models.TextField('данные ответа', null=True, blank=True)
    query_params = models.JSONField('get-параметры', default=dict, blank=True)

    remote_addr = models.GenericIPAddressField(null=True, blank=True)
    host = models.URLField()
    method = models.CharField(max_length=10)
    user_agent = models.CharField(max_length=255, blank=True)
    errors = models.TextField(null=True, blank=True)
    status_code = models.PositiveIntegerField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ('-requested_at',)
        verbose_name = 'API Request Log'

    def __str__(self):
        return f'{self.method} {self.path}'
