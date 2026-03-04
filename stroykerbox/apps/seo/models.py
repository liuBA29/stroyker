from django.db import models
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _

from ckeditor.fields import RichTextField


class RobotsTxt(models.Model):
    site = models.OneToOneField(
        Site,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    content = models.TextField(_('robots.txt file content'), blank=True, default='')

    def __str__(self):
        return self.site.name

    class Meta:
        verbose_name = _('robots.txt file')
        verbose_name_plural = _('robots.txt files')


class MetaTag(models.Model):
    """Meta tags defined by user"""

    url = models.CharField(
        _('url'),
        max_length=255,
        unique=True,
        help_text=_('always use full page path with trailing slash: "/news/", "/"'),
    )
    title = models.CharField(
        _('title'),
        max_length=255,
        help_text=_('Override &lt;title tag'),
        blank=True,
        default='',
    )
    h1 = models.TextField(
        _('h1'),
        max_length=255,
        help_text=_('Override &lt;h1&gt; tag contents'),
        blank=True,
        default='',
    )
    meta_keywords = models.TextField(_('meta keywords'), blank=True, default='')
    meta_description = models.TextField(_('meta description'), blank=True, default='')
    seo_text = RichTextField(
        _('seo text'),
        blank=True,
        null=True,
        help_text=_(
            'Formatted and optimized text to attract the attention of search engines.'
        ),
    )

    # https://redmine.nastroyker.ru/issues/19418
    ai_keywords = models.TextField(
        blank=True, default='', help_text=('Ключевые слова для ИИ.')
    )

    def __str__(self):
        return self.url

    class Meta:
        verbose_name = _('meta tag')
        verbose_name_plural = _('meta tags')
