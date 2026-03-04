from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache

from uuslug import slugify
from django_geoip.models import City


class Location(models.Model):
    """
    The location object of the store’s branch.
    """

    name = models.CharField(_('location name'), max_length=255, unique=True)
    city = models.OneToOneField(
        City, on_delete=models.CASCADE, related_name='location', null=True, blank=True
    )
    is_default = models.BooleanField(
        default=False, help_text=_('Set this location as default.')
    )
    is_active = models.BooleanField(
        default=True, help_text=_('Enable or disable this location.')
    )
    slug = models.SlugField(_('slug'), unique=True, default='')
    latitude = models.DecimalField(
        _('center latitude'), max_digits=9, decimal_places=6
    )
    longitude = models.DecimalField(
        _('center longitude'), max_digits=9, decimal_places=6
    )
    position = models.PositiveSmallIntegerField(_('position'), default=0, db_index=True)
    email = models.EmailField(null=True, blank=True)

    class Meta:
        verbose_name = _('location')
        verbose_name_plural = _('locations')
        ordering = (
            'position',
            'pk',
        )

    def __str__(self):
        return self.name

    def clean(self):
        coords = [self.latitude, self.longitude]
        if any(coords) and not all(coords):
            raise ValidationError(
                _(
                    'You must to set the coordinates for latitude and longitude, '
                    'or not set them at all.'
                )
            )

        if self.is_default:
            if not self.is_active:
                raise ValidationError(_('You cannot disable the default location.'))
        elif (
            not self.__class__.objects.filter(is_default=True)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError(
                _(
                    'There is no default location. Before changing the data '
                    'of existing locations, you must set the default location.'
                )
            )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        return super().save(*args, **kwargs)

    CACHE_KEY_PREFIX = 'locations'

    @property
    def center_latitude(self):
        return self.latitude

    @property
    def center_longitude(self):
        return self.longitude

    @classmethod
    def _available_locations_cache_key(cls):
        return f'{cls.CACHE_KEY_PREFIX}:available_locations'

    @classmethod
    def _default_location_cache_key(cls):
        return f'{cls.CACHE_KEY_PREFIX}:default_location'

    @classmethod
    def get_by_ip_range(cls, ip_range):
        """
        IpRange has one to many relationship with Country, Region and City.
        Here we exploit the later relationship.
        """
        if hasattr(ip_range, 'city'):
            return cls.objects.get(is_active=True, city=ip_range.city)

    @classmethod
    def check_default(cls, location):
        """
        Checking the passed location whether it is the default location.
        """
        default_location = cls.get_default_location()
        if not location or not default_location:
            # If the default location does not setted, then we believe
            # that we have only one location.
            return True
        return hasattr(location, 'id') and location.id is default_location.id

    @classmethod
    def get_default_location(cls):
        obj = cache.get(cls._default_location_cache_key())
        if not obj:
            obj = cls.objects.filter(is_default=True, is_active=True).first()
            cache.set(cls._default_location_cache_key(), obj)
        return obj

    @classmethod
    def get_available_locations(cls):
        return cache.get_or_set(
            cls._available_locations_cache_key(), cls.objects.filter(is_active=True)
        )


class LocationPhone(models.Model):
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name='phones'
    )
    phone = models.CharField(_('formated phone'), max_length=32)
    phone_raw = models.CharField(_('phone for url'), max_length=16)
    position = models.PositiveSmallIntegerField(_('position'), default=0)

    class Meta:
        ordering = ('position',)
        verbose_name = _('location phone')
        verbose_name_plural = _('location phones')

    def __str__(self):
        return self.phone
