from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError

from mptt.models import MPTTModel
from mptt.fields import TreeForeignKey
from colorfield.fields import ColorField

from stroykerbox.apps.utils.validators import validator_svg
from stroykerbox.apps.utils.validators import validate_svg_or_image


class Menu(models.Model):
    key = models.CharField(_('menu key'), primary_key=True, max_length=60,
                           help_text=_('Key is used in the code, do not modify it'))
    title = models.CharField(_('menu title'), max_length=255)

    def __str__(self):
        return self.title

    @property
    def get_published_items(self):
        return self.items.filter(published=True).order_by('position')

    class Meta:
        verbose_name = _('menu')
        verbose_name_plural = _('menus')


class MenuItem(MPTTModel):
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE,
                             related_name='items', verbose_name=_('menu'))
    parent = TreeForeignKey('self', verbose_name=_('parent menu item'),
                            null=True, blank=True, related_name='children',
                            on_delete=models.SET_NULL, )
    anchor = models.CharField(_('anchor'), max_length=50)
    title = models.CharField(_('link title attribute'), max_length=50)
    url = models.CharField('url', max_length=255)
    icon = models.FileField(
        verbose_name=_('menu icon'), upload_to='menu/images/icons', blank=True, null=True)
    download = models.BooleanField(_('download link'), default=False)
    position = models.PositiveSmallIntegerField(_('position'), default=0)
    published = models.BooleanField(_('hide or show item'), default=True)
    css_class = models.CharField(_('css class'), max_length=16, null=True, blank=True)
    new_tab = models.BooleanField(_('open in new tab'), default=False)

    def __str__(self):
        return f'{self.anchor} {self.url}'

    class MPTTMeta:
        verbose_name = _('menu item')
        verbose_name_plural = _('menu items')
        ordering = ('position',)


class CustomNavigation(models.Model):
    """
    Custom Navigation block
    """
    key = models.CharField(_('key'), max_length=32, help_text=_(
        'This value is used in the code, do not touch it!'))
    title = models.CharField(_('name'), max_length=70)
    comment = models.CharField(
        _('comment'), max_length=255, blank=True, null=True)
    bg_color = ColorField(_('background color'), null=True, blank=True)
    bg_image = models.FileField(verbose_name=_('background image'), upload_to='menu/images',
                                validators=[validate_svg_or_image],
                                blank=True, null=True)
    top_indent = models.SmallIntegerField(_('top indent, px'), null=True, blank=True,
                                          help_text=_('Top indent for the block (in pixels).'))
    bottom_indent = models.SmallIntegerField(_('bottom indent, px'), null=True, blank=True,
                                             help_text=_('Bottom indent for the block (in pixels).'))
    published = models.BooleanField(_('published'), default=True)

    def __str__(self):
        return str(self.title)

    class Meta:
        verbose_name = _('custom navigation')
        verbose_name_plural = _('custom navigations')


class CustomLink(models.Model):
    """
    Navigation link
    """
    navigation = models.ForeignKey(
        CustomNavigation, on_delete=models.CASCADE, related_name='links')
    name = models.CharField(_('name'), max_length=70)
    url = models.CharField(_('url'), db_index=True, max_length=255, help_text=_(
        'Example: "/about/" or "/"'))
    image = models.ImageField(
        _('image'), upload_to='navigation/images', blank=True, null=True)
    svg = models.FileField(
        verbose_name=_('svg image'), upload_to='navigation/images',
        blank=True, null=True, validators=[validator_svg])
    position = models.PositiveIntegerField(_('position'), default=0)

    class Meta:
        verbose_name = _('navigation link')
        verbose_name_plural = _('navigation links')
        ordering = ['position']

    def __str__(self):
        return str(self.name)

    def clean(self):
        if not self.image and not self.svg:
            raise ValidationError(_('Image file not specified'))
        elif self.image and self.svg:
            raise ValidationError(_('You must to upload just one thing: either '
                                    'an image or an SVG file, not both.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def image_file(self):
        return self.image or self.svg
