from typing import Optional
from decimal import Decimal
from urllib.parse import urlparse

from django.db import models
from django.core import validators
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.functional import cached_property
from uuslug import uuslug
from colorfield.fields import ColorField

from stroykerbox.apps.locations.models import Location

YANDEX_MAP_COLORS = (
    ('blue', _('blue')),
    ('red', _('red')),
    ('darkOrange', _('dark orange')),
    ('night', _('night')),
    ('darkBlue', _('dark blue')),
    ('pink', _('pink')),
    ('gray', _('gray')),
    ('brown', _('brown')),
    ('darkGreen', _('dark green')),
    ('violet', _('violet')),
    ('black', _('black')),
    ('yellow', _('yellow')),
    ('green', _('green')),
    ('orange', _('orange')),
    ('lightBlue', _('light blue')),
    ('olive', _('olive')),
)


class AddressModelBaseAbstract(models.Model):
    name = models.CharField(_('name'), max_length=60, unique=True)
    address = models.CharField(_('address'), max_length=256)
    phone = models.CharField(
        _('phone'),
        max_length=11,
        validators=[
            validators.RegexValidator(
                r'^[78][\d]{10}$',
                _(
                    'Enter a valid phone number starting with "7 (or 8)" '
                    'followed by 10 digits.'
                ),
                'invalid',
            )
        ],
    )
    email = models.EmailField(_('email'), max_length=60, null=True, blank=True)
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, verbose_name=_('location')
    )
    created_at = models.DateTimeField(_('created date'), auto_now_add=True)
    updated_at = models.DateTimeField(_('update date'), auto_now=True)
    is_active = models.BooleanField(default=True)
    slug = models.SlugField(_('slug'), null=True)
    ymap_icon_color = models.CharField(
        _('icon color'), max_length=16, choices=YANDEX_MAP_COLORS, null=True, blank=True
    )
    ymap_glyph_icon = models.CharField(
        _('glyph icon name'), max_length=32, null=True, blank=True
    )
    ymap_glyph_color = ColorField(_('glyph icon color'), null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuslug(self.name, instance=self)
        return super().save(*args, **kwargs)


class AddressModelAbstract(AddressModelBaseAbstract):
    geo_latitude = models.DecimalField(
        _('latitude'),
        max_digits=9,
        decimal_places=6,
        help_text=_('latitude of the partner location'),
    )
    geo_longitude = models.DecimalField(
        _('longitude'),
        max_digits=9,
        decimal_places=6,
        help_text=_('longitude of the partner location'),
    )

    class Meta:
        abstract = True


class Partner(AddressModelBaseAbstract):
    name = models.CharField(_('name'), max_length=60)
    phone = models.CharField(
        _('phone'),
        max_length=11,
        validators=[
            validators.RegexValidator(
                r'^[78][\d]{10}$',
                _(
                    'Enter a valid phone number starting with "7 (or 8)" '
                    'followed by 10 digits.'
                ),
                'invalid',
            )
        ],
        null=True,
        blank=True,
    )
    website = models.URLField(_('site url'), null=True, blank=True)
    description = models.TextField(_('description'), null=True, blank=True)
    position = models.PositiveIntegerField(_('position'), default=0)
    page_url = models.CharField(
        'страница партнера',
        max_length=255,
        help_text='Внутренняя ссылка на страницу партнера, если такая есть.',
        null=True,
        blank=True,
        validators=[
            validators.RegexValidator(
                '^/([a-z0-9-_A-Z]+/)*',
                message='Внутренний URL должен начинаться и заканчиваться слешем.',
            )
        ],
    )
    category = models.ForeignKey(
        'PartnerCategory',
        verbose_name='категория',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    city = models.ForeignKey(
        'PartnerCity',
        verbose_name='город',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ('position',)
        default_related_name = 'partners'
        verbose_name = _('partner')
        verbose_name_plural = _('partners')

    @property
    def website_name(self):
        parsed = urlparse(self.website)
        scheme = "%s://" % parsed.scheme
        return self.website.replace(scheme, '', 1)


class PartnerCoordinates(models.Model):
    """
    https://redmine.nastroyker.ru/issues/16558
    """

    partner = models.ForeignKey(
        Partner, on_delete=models.CASCADE, related_name='coordinates'
    )
    coordinates = models.CharField(
        'широта/долгота',
        max_length=32,
        help_text=(
            'Ввод через запятую, последовательность обязательна: '
            'сначала - широта, затем - долгота.'
        ),
    )

    class Meta:
        verbose_name = 'координаты партнера'
        verbose_name_plural = 'координаты партнера'

    def __str__(self):
        return self.coordinates

    @cached_property
    def geo_latitude(self) -> Optional[Decimal]:
        """
        Координаты широты.
        """
        try:
            latitude = self.coordinates.split(',')[0].strip()
            return Decimal(latitude)
        except Exception:
            pass

    @cached_property
    def geo_longitude(self) -> Optional[Decimal]:
        """
        Координаты долготы.
        """
        try:
            longitude = self.coordinates.split(',')[1].strip()
            return Decimal(longitude)
        except Exception:
            pass


class PartnerCategory(models.Model):
    name = models.CharField('название', max_length=64)
    position = models.PositiveSmallIntegerField('позиция', default=0)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ('position',)
        verbose_name = 'категория партнера'
        verbose_name_plural = 'категории партнеров'

    def __str__(self):
        return self.name


class PartnerCity(models.Model):
    """
    https://redmine.nastroyker.ru/issues/16738#change-89523
    """

    name = models.CharField('название', max_length=64)
    position = models.PositiveSmallIntegerField('позиция', default=0)
    slug = models.SlugField(unique=True)

    class Meta:
        ordering = ('position',)
        verbose_name = 'город партнера'
        verbose_name_plural = 'города партнеров'

    def __str__(self):
        return self.name


class Contact(AddressModelAbstract):
    phone = models.CharField(_('phone'), max_length=64)
    position = models.PositiveSmallIntegerField(_('position'), default=0)
    extra = models.TextField(_('extra info'), null=True, blank=True)

    class Meta:
        default_related_name = 'contacts'
        verbose_name = _('contact')
        verbose_name_plural = _('contacts')
        ordering = ('position',)

    def get_absolute_url(self):
        return reverse('contacts-page')
