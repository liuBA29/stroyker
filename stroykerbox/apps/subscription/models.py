from django.db import models
from django.utils.translation import ugettext_lazy as _


class Subscription(models.Model):
    email = models.EmailField(_('email address'), unique=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    def __str__(self):
        return self.email

    class Meta:
        ordering = ('-created_at', )
        verbose_name = _('subscription')
        verbose_name_plural = _('subscriptions')
