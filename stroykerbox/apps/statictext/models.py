from django.db import models
from django.utils.translation import ugettext_lazy as _


class Statictext(models.Model):
    """
    Static text used it templates
    """
    key = models.CharField(_('key'), max_length=70, unique=True,
                           help_text=_('This value is used in the code. Do not touch it!'))
    text = models.TextField(_('text'), blank=True, null=True)
    comment = models.CharField(
        _('comment'), max_length=255, blank=True, null=True)
    use_editor = models.BooleanField(_('use editor'), default=False)
    use_custom_form = models.BooleanField(
        _('use custom form'), default=False,
        help_text=_('Uses the custom form inside text. '
                    'To insert the desired custom form use the syntax: {% custom_form "CUSTOM-FORM-KEY" %}'))

    def __str__(self):
        return str(self.comment)

    class Meta:
        verbose_name = _('static text')
        verbose_name_plural = _('static texts')
