from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.html import strip_tags
from django.utils.text import Truncator


class Question(models.Model):
    """
    Question/Answer object model.
    """
    question = models.TextField(_('question'))
    answer = models.TextField(_('answer'))
    position = models.PositiveSmallIntegerField(_('position'), default=0)
    opened = models.BooleanField(_('opened'), default=False)
    published = models.BooleanField(_('published'), default=True)
    frontpage = models.BooleanField(_('show on frontpage'), default=False)

    def __str__(self):
        text = strip_tags(self.question)
        return Truncator(text).words(5)

    class Meta:
        ordering = ['position']
        verbose_name = _('question')
        verbose_name_plural = _('questions')
