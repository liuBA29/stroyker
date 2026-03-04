import os.path
from urllib.parse import urlparse

from django.utils import timezone
from django.core.validators import RegexValidator
from django.db import models
from django.urls import Resolver404, resolve
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.utils.functional import cached_property

from constance import config
from mptt.models import MPTTModel, TreeForeignKey, TreeManager
from stroykerbox.apps.utils.validators import validator_svg, validate_svg_or_image
from stroykerbox.apps.catalog.models import ProductSet


class PageManager(TreeManager):
    """
    Page custom manager
    """

    def get_active_page(self, uri):
        """
        Get current active page from request
        """
        try:
            page = self.get(url=str(uri), published=True)
        except Page.DoesNotExist:
            parsed = urlparse(uri)
            try:
                page = self.get(url=str(parsed.path), published=True)
            except Page.DoesNotExist:
                try:
                    page = self.get(url__startswith=str(parsed.path), published=True)
                except Page.DoesNotExist:
                    # try to find related page
                    try:
                        view_func = resolve(parsed.path).func
                        if hasattr(view_func, 'related_page_url'):
                            page = self.get_active_page(
                                getattr(view_func, 'related_page_url')
                            )
                        else:
                            raise
                    except Resolver404:
                        raise
        return page


class File(models.Model):
    """
    File attached to a page
    """

    name = models.CharField(_('name'), max_length=140, null=True, blank=True)
    file = models.FileField(_('file'), upload_to='staticpages')  # noqa: ignore=B001
    page = models.ForeignKey('Page', on_delete=models.CASCADE, related_name='files')
    position = models.PositiveIntegerField(_('position'), default=0, blank=True)

    class Meta:
        ordering = ('position',)
        verbose_name = 'файл'
        verbose_name_plural = 'файлы'

    def __str__(self):
        if self.name:
            return self.name
        return self.file.url

    @property
    def extension(self):
        return os.path.splitext(self.file.path)[1]


class PageImage(models.Model):
    """
    Image in page
    """

    title = models.CharField(_('title'), max_length=140, null=True, blank=True)
    image = models.FileField(_('image'), upload_to='staticpages')
    page = models.ForeignKey('Page', on_delete=models.CASCADE, related_name='images')
    position = models.PositiveIntegerField(
        _('position'), db_index=True, default=0, blank=True
    )

    def __str__(self):
        if self.title:
            return self.title
        return self.image.url

    class Meta:
        ordering = ['position', 'id']
        verbose_name = _('image')
        verbose_name_plural = _('images')


class Page(MPTTModel):
    """Page"""

    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        verbose_name=_('parent page'),
        null=True,
        blank=True,
        related_name='children',
    )
    title = models.CharField(_('title tag'), max_length=255)
    key = models.CharField(
        _('key'),
        help_text=_('Key is used in the code, do not modify it'),
        db_index=True,
        max_length=70,
        blank=True,
        default='',
    )
    url = models.CharField(
        _('url'),
        max_length=255,
        help_text=_('Page full path: /news/ or /'),
        unique=True,
        validators=[
            RegexValidator(
                '^/([a-z0-9-_A-Z]+/)*', message=_('Must start and end with slash')
            )
        ],
    )
    text = models.TextField(
        _('text'),
        blank=True,
        null=True,
        help_text=_('HTML content of the page if it is static'),
    )
    published = models.BooleanField(
        _('published'),
        help_text=_('The page will not be shown at the site until it is published'),
        db_index=True,
        default=False,
    )
    meta_keywords = models.TextField(_('meta keywords'), blank=True, null=True)
    meta_description = models.TextField(_('meta description'), blank=True, null=True)
    position = models.PositiveSmallIntegerField('Position', null=False, default=0)
    wide_view = models.BooleanField(_('wide view mode'), default=True)
    container = models.BooleanField(
        _('container for child pages'),
        default=False,
        help_text=_('Check if this is a container page for child pages.'),
    )
    icon = models.FileField(
        verbose_name=_('icon (svg)'),
        upload_to='staticpages/svg',
        blank=True,
        null=True,
        validators=[validator_svg],
    )
    teaser_image = models.FileField(
        _('teaser image'),
        upload_to='staticpages/images',
        validators=[validate_svg_or_image],
        blank=True,
        null=True,
    )
    updated_at = models.DateTimeField(
        _('date and time of update'), auto_now=timezone.now()
    )
    no_wrapper = models.BooleanField(
        _('don`t use wrapper'),
        default=False,
        help_text=_('Use the html-code of the page as is, without using a wrapper.'),
    )
    related_productset = models.ForeignKey(
        ProductSet,
        verbose_name=_('related product set'),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    search_document = SearchVectorField(null=True, blank=True)

    # https://redmine.nastroyker.ru/issues/19241
    use_editor = models.BooleanField(
        'использовать редактор',
        default=True,
    )

    objects = PageManager()

    class Meta:
        verbose_name = _('page')
        verbose_name_plural = _('pages')
        ordering = ['position']
        indexes = [GinIndex(fields=['search_document'])]

    class MPTTMeta:
        order_insertion_by = ['position']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return self.url

    def index_components(self):
        """
        Returns the weight and value of the fields to be entered in the search index (search_document field).
        This method will be called when the product is saved (by signal) to update the search index.
        """
        components = {}
        if config.SEARCH_STATICPAGE_TITLE:
            components['A'] = self.title
        if config.SEARCH_STATICPAGE_TEXT:
            components['B'] = self.text
        return components

    def get_children_with_order(self):
        return (
            self.get_children()
            .values('title', 'url', 'position', 'icon')
            .order_by('position')
        )

    def _get_custom_staticfile(self, ext):
        return [
            f.file.url
            for f in self.custom_staticfiles.filter(file_type=ext).only('file')
        ]

    @cached_property
    def custom_css(self):
        return self._get_custom_staticfile('css')

    @cached_property
    def custom_js(self):
        return self._get_custom_staticfile('js')


def get_page_url(key):
    """
    Get page url by its key
    """
    page = Page.objects.get(key=key)
    return page.get_absolute_url()


class PageCustomStaticfile(models.Model):
    POSSIBLE_EXTENSIONS: set | tuple = ('css', 'js')

    page = models.ForeignKey(
        Page, on_delete=models.CASCADE, related_name='custom_staticfiles'
    )
    file = models.FileField(_('file'), upload_to='staticpages/custom_staticfiles/')
    file_type = models.CharField(_('file type'), max_length=4, null=True, blank=True)
    position = models.PositiveSmallIntegerField(_('position'), default=0)

    class Meta:
        ordering = ['position']
        verbose_name = _('page custom staticfile')
        verbose_name_plural = _('page custom staticfiles')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._swap_class()

    def __str__(self):
        return os.path.basename(self.file.name)

    def save(self, *args, **kwargs):
        self.clean()
        self._swap_class()
        return super().save(*args, **kwargs)

    def clean(self):
        extension = self.file.name.split('.')[-1]
        if extension not in self.POSSIBLE_EXTENSIONS:
            raise ValidationError(
                _('Possible file extensions: %(file_types)s')
                % {'file_types': ', '.join(self.POSSIBLE_EXTENSIONS)}
            )
        self.file_type = extension

    def _swap_class(self):
        if self.file_type:
            self.__class__ = EXTENSION_TO_CLASS_MAPPER[self.file_type]


class PageCustomCss(PageCustomStaticfile):
    POSSIBLE_EXTENSIONS = {'css'}

    class Meta:
        proxy = True
        verbose_name = _('custom css file')
        verbose_name_plural = _('custom css files')


class PageCustomJs(PageCustomStaticfile):
    POSSIBLE_EXTENSIONS = {'js'}

    class Meta:
        proxy = True
        verbose_name = _('custom js file')
        verbose_name_plural = _('custom js files')


EXTENSION_TO_CLASS_MAPPER = {
    'css': PageCustomCss,
    'js': PageCustomJs,
}

# Для избежания ошибки с циклическим импортом, когда запрашивается список шаблонных тегов
# описание модели Страницы-Конструктора и ее методов подгружаем в самую последнюю очередь.
from .constructor_models import *  # noqa
