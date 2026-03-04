from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from stroykerbox.apps.utils.validators import (validator_svg, url_or_path_validator,
                                               validate_svg_or_image)


class SlideBaseAbstract(models.Model):
    name = models.CharField(_('name'), max_length=128)
    published = models.BooleanField(
        _('published'), default=True, db_index=True)
    position = models.PositiveIntegerField(_('position'), default=0)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class BigSlide(SlideBaseAbstract):
    image = models.ImageField(
        _('image'), upload_to='slides/big_slides', blank=True, null=True)
    svg = models.FileField(
        verbose_name=_('svg image'), upload_to='slides/big_slides/svg',
        blank=True, null=True, validators=[validator_svg])
    content = models.TextField(
        _('content'), blank=True, null=True, help_text=_('slide content'))
    url = models.CharField(_('url'), max_length=255,
                           validators=[url_or_path_validator],
                           blank=True, null=True, help_text=_('Link URL'))

    class Meta:
        ordering = ['position']
        verbose_name = _('big slide')
        verbose_name_plural = _('big slides')

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


class PartnerSlide(SlideBaseAbstract):
    logo = models.ImageField(
        _('partner logo'), upload_to='slides/partner_slides', blank=True, null=True)
    svg_logo = models.FileField(
        verbose_name=_('partner logo as svg'), upload_to='slides/partner_slides/svg',
        blank=True, null=True, validators=[validator_svg])
    url = models.URLField(_('partner url'), max_length=255,
                          blank=True, null=True, help_text=_('External Link URL'))

    class Meta:
        ordering = ['-position']
        verbose_name = _('partner slide')
        verbose_name_plural = _('partner slides')

    def clean(self):
        if not self.logo and not self.svg_logo:
            raise ValidationError(_('Image file not specified'))
        elif self.logo and self.svg_logo:
            raise ValidationError(_('You must to upload just one thing: either '
                                    'an image or an SVG file, not both.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def image_file(self):
        return self.logo or self.svg_logo


SLIDER_SET_COLS_MAP = {
    2: '',
    3: '',
    4: '',
    5: '',
    6: '',
}


class SliderSet(models.Model):
    key = models.SlugField(_('key'), max_length=70, unique=True,
                           help_text=_('This value is used in the code. Do not touch it!'))
    name = models.CharField(_('name'), max_length=128)
    use_autoplay = models.BooleanField(_('use autoplay'), default=False)
    autoplay_timeout = models.PositiveIntegerField(
        _('autoplay timeout, ms'), default=5000)
    arrow_right = models.FileField(
        verbose_name=_('right arrow'), upload_to='slides/',
        blank=True, null=True, validators=[validate_svg_or_image])
    arrow_left = models.FileField(
        verbose_name=_('left arrow'), upload_to='slides/',
        blank=True, null=True, validators=[validate_svg_or_image])
    zoom_effect = models.BooleanField(_('use zoom effect'), default=False)
    arrows_type = models.CharField('arrows type', max_length=8,
                                   choices=(
                                       ('arrows', 'стрелки сверху'),
                                       ('dots', 'точки снизу'),
                                   ), default='arrows')
    data_rows = models.PositiveSmallIntegerField(
        'data-rows', default=1)
    data_slides = models.PositiveSmallIntegerField(
        'data-slides', default=1)
    data_sm_slides = models.PositiveSmallIntegerField(
        'data-sm-slides', default=1)
    data_md_slides = models.PositiveSmallIntegerField(
        'data-md-slides', default=2)
    data_lg_slides = models.PositiveSmallIntegerField(
        'data-lg-slides', default=3)
    data_xl_slides = models.PositiveSmallIntegerField(
        'data-xl-slides', default=5)

    class Meta:
        verbose_name = _('slider set')
        verbose_name_plural = _('slider sets')

    def __str__(self):
        return self.name


class SliderSetItem(models.Model):
    sliderset = models.ForeignKey(
        SliderSet, on_delete=models.CASCADE, related_name='sliderset_items')
    image = models.ImageField(
        _('image'), upload_to='slides/big_slides', blank=True, null=True)
    svg = models.FileField(
        verbose_name=_('svg image'), upload_to='slides/big_slides/svg',
        blank=True, null=True, validators=[validator_svg])
    url = models.CharField(_('url'), max_length=255,
                           validators=[url_or_path_validator],
                           blank=True, null=True, help_text=_('Link URL'))
    text = models.TextField(_('text content'), blank=True, null=True)
    img_open_full = models.BooleanField(
        _('open image in full size'), default=False)
    hide_adaptive = models.BooleanField(_('hide in adaptive'), default=False)
    position = models.PositiveIntegerField(_('position'), default=0)

    class Meta:
        ordering = ['position']
        verbose_name = _('slider set item')
        verbose_name_plural = _('slider set items')

    def __str__(self):
        return self.image_file.name if self.image_file else f'{self.sliderset}:{self.pk}'

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def clean(self):
        if self.image and self.svg:
            raise ValidationError(_('You must to upload just one thing: either '
                                    'an image or an SVG file, not both.'))

    @property
    def image_file(self):
        return self.image or self.svg
