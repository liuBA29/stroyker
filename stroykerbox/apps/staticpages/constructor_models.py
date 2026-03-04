from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property

from stroykerbox.apps.customization.models import TagContainerItemAbstract  # noqa


class PageContructor(models.Model):
    title = models.CharField(_('title tag'), max_length=255)
    key = models.CharField(_('key'), help_text=_('Key is used in the code, do not modify it'), db_index=True,
                           max_length=70, blank=True, default='')
    url = models.CharField(_('url'), max_length=255,
                           help_text=_('Page full path: /news/ or /'), unique=True,
                           validators=[
                               RegexValidator('^/([a-z0-9-_A-Z]+/)*', message=_('Must start and end with slash'))])
    published = models.BooleanField(_('published'),
                                    help_text=_(
                                        'The page will not be shown at the site until it is published'),
                                    db_index=True, default=False)
    position = models.PositiveSmallIntegerField(_('position'), default=0)
    meta_keywords = models.TextField(_('meta keywords'), blank=True, null=True)
    meta_description = models.TextField(
        _('meta description'), blank=True, null=True)
    cache = models.BooleanField(_('cache enabled'), default=False)
    cache_timeout = models.PositiveIntegerField(
        _('cache timeout, sec'), blank=True, null=True)

    class Meta:
        verbose_name = _('contructor page')
        verbose_name_plural = _('contructor pages')
        ordering = ['position']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return self.url

    @property
    def cache_key(self):
        return f'statipage_contructor:{self.key}:{self.url}:{self.published}:{self.position}'

    @cached_property
    def custom_css(self):
        return [f.file.url for f in self.custom_files.filter(type='css').only('file')]

    @cached_property
    def custom_js(self):
        return [f.file.url for f in self.custom_files.filter(type='js').only('file')]


class PageContructorBlock(TagContainerItemAbstract):
    page = models.ForeignKey(PageContructor,
                             on_delete=models.CASCADE, related_name='blocks')


class PageParendBreadcrumb(models.Model):
    page = models.ForeignKey(
        PageContructor, on_delete=models.CASCADE, related_name='breadcrumbs')
    title = models.CharField(_('title tag'), max_length=128)
    link = models.CharField(_('link'), max_length=255)
    position = models.PositiveSmallIntegerField(_('position'), default=0)

    class Meta:
        ordering = ['position']
        verbose_name = _('page parent breadcrumb')
        verbose_name_plural = _('page parent breadcrumbs')

    def __str__(self):
        return self.title


class PageCustomFiles(models.Model):
    page = models.ForeignKey(
        PageContructor, on_delete=models.CASCADE, related_name='custom_files')
    file = models.FileField(
        _('Custom file'), upload_to='staticpages/custom/files')
    type = models.CharField(_('type'), max_length=3,
                            choices=(('css', 'css'), ('js', 'js')))
    position = models.PositiveSmallIntegerField(_('position'), default=0)

    class Meta:
        ordering = ['position', 'pk']
        verbose_name = _('page custom css/js file')
        verbose_name_plural = _('page custom css/js files')
