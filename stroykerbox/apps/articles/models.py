from django.db import models
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError

from ckeditor.fields import RichTextField
from sorl.thumbnail import ImageField
from stroykerbox.apps.catalog.models import Product


class Article(models.Model):
    """
    Article object.
    """
    title = models.CharField(_('title'), max_length=255)
    teaser = RichTextField(_('teaser text'))
    body = RichTextField(_('article body'))
    label = models.CharField(_('label'), max_length=60,
                             help_text=_('Text label for article tagging.'))
    image = ImageField(_('image'), upload_to='articles', blank=True)
    wide_view = models.BooleanField(_('wide view mode'), default=True)
    published = models.BooleanField(
        _('show on the site'), db_index=True, default=True, )
    slug = models.SlugField(unique=True)
    created = models.DateTimeField(
        _('creation date'), default=timezone.now, blank=True)
    related_products = models.ManyToManyField(
        Product, verbose_name=_('related products'), blank=True)
    related_products_title = models.CharField(
        _('title of the related products block'), max_length=255, null=True, blank=True)
    use_custom_form = models.BooleanField(
        _('use custom form'), default=False,
        help_text=_('Uses the custom form inside text. '
                    'To insert the desired custom form use the syntax: {% custom_form "CUSTOM-FORM-KEY" %}'))
    meta_keywords = models.TextField(_('meta keywords'), blank=True, null=True)
    meta_description = models.TextField(
        _('meta description'), blank=True, null=True)

    def __str__(self):
        return str(self.title)

    def get_absolute_url(self):
        return reverse('articles:article-details', kwargs={'slug': self.slug})

    class Meta:
        ordering = ['-created', '-pk']
        verbose_name = _('article')
        verbose_name_plural = _('articles')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        if self.pk and self.related_products.exists() and not self.related_products_title:
            raise ValidationError(_('You must to set a title for the block of related products.'))
