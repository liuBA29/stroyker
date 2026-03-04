from datetime import timedelta

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import IntegerRangeField
from django.contrib.postgres.validators import RangeMinValueValidator, RangeMaxValueValidator
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils.functional import cached_property

User = get_user_model()


class Item(models.Model):
    itemset = models.ForeignKey('booking.ItemSet',
                                verbose_name=_('набор слотов'),
                                related_name='items', on_delete=models.CASCADE)
    name = models.CharField(_('название слота'), max_length=255, unique=True)

    class Meta:
        unique_together = (('itemset', 'name'),)
        verbose_name = _('слот брони')
        verbose_name_plural = _('слоты брони')

    def __str__(self):
        return self.name


class ItemSetHourRange(models.Model):
    itemset = models.ForeignKey(
        'booking.ItemSet', verbose_name=_('набор'), related_name='hour_ranges',
        on_delete=models.CASCADE)
    hours_range = IntegerRangeField(_('диапазон часов'), validators=(
        RangeMinValueValidator(0),
        RangeMaxValueValidator(23)
    ))

    class Meta:
        verbose_name = _('диапазон часов для наборов слотов брони')
        verbose_name_plural = _('диапазоны часов для наборов слотов брони')

    def __str__(self):
        return f'{self.itemset.name}:{self.hours_range}'


class ItemSet(models.Model):
    key = models.SlugField(_('ключ'), primary_key=True, max_length=70,
                           help_text=_('The value should only consist of Latin letters, numbers, '
                                       'underscores or hyphens.'))
    name = models.CharField(_('название'), max_length=255)
    published = models.BooleanField(_('опубликована'), default=True)
    html_top = models.TextField(
        _('html перед таблицей'), null=True, blank=True)
    html_middle = models.TextField(
        _('html после таблицы'), null=True, blank=True)
    html_bottom = models.TextField(
        _('html после формы'), null=True, blank=True)

    # https://redmine.fancymedia.ru/issues/11985
    slots_ahead = models.PositiveSmallIntegerField('кол-во бронирований вперед',
                                                   blank=True, null=True,
                                                   help_text=('Кол-во слотов, рассположенных за выбранным, '
                                                              'и бронируемых вместе с выбранным.'))
    form_title = models.CharField(
        'заголовок формы заказа', max_length=255, null=True, blank=True)
    form_text = models.TextField(
        'текс формы заказа', null=True, blank=True)

    class Meta:
        verbose_name = _('набор слотов брони')
        verbose_name_plural = _('наборы слотов брони')

    def __str__(self):
        return self.key

    def get_absolute_url(self, custom_date=None):
        if custom_date:
            return reverse('booking:matrix_page_custom_date', args=(self.key, custom_date))
        else:
            return reverse('booking:matrix_page', args=(self.key,))

    @cached_property
    def hours_set(self):
        hours = set()
        for r in self.hour_ranges.all():
            hours |= set(range(r.hours_range.lower, r.hours_range.upper + 1))
        return hours


class ItemReserve(models.Model):
    item = models.ForeignKey(
        'booking.Item', on_delete=models.CASCADE, related_name='reserves')
    date = models.DateField(_('дата'))
    hour = models.PositiveIntegerField(
        'час', choices=[(h, h) for h in range(24)], null=True, blank=True)
    comment = models.CharField(
        _('комментарий'), max_length=256, null=True, blank=True)
    name = models.CharField(_('имя'), max_length=128, null=True)
    phone = models.CharField(_('телефон для связи'), max_length=18, null=True)
    no_notify = models.BooleanField(editable=False, default=False)

    class Meta:
        unique_together = (('item', 'date', 'hour'),)
        verbose_name = _('бронирование')
        verbose_name_plural = _('бронирования')

    def __str__(self):
        output = f'{self.item}:{self.date}'
        if self.hour:
            output += f':{self.hour}'
        return output

    def create_ahead_slots_reserve(self):
        """
        https://redmine.fancymedia.ru/issues/11985
        Создаем связанные резервы, если в наборе установлено соответствующее значение для запуска
        этого действия.
        """
        if not self.item.itemset.slots_ahead:
            return

        hours_list = list(self.item.itemset.hours_set)

        for i in range(1, self.item.itemset.slots_ahead + 1):
            if self.hour is not None:
                try:
                    hour = hours_list[hours_list.index(self.hour) + i]
                except IndexError:
                    continue
                date = self.date
            else:
                date = self.date + timedelta(days=i)
                hour = None

            main_params = dict(
                item=self.item, date=date, hour=hour)
            defaults = dict(
                phone=self.phone,
                comment=self.comment,
                name=self.name,
                no_notify=True
            )

            self.__class__.objects.get_or_create(
                **main_params,
                defaults=defaults
            )

    def clean(self):
        if self.item.itemset.hours_set:
            if self.hour is None:
                raise ValidationError(
                    {'hour': _('Необходимо ввести час брони.')})
            elif self.hour not in self.item.itemset.hours_set:
                raise ValidationError({'hour': _(
                    'Выбранный час не входит в диапазон часов, установленный для данной матрицы.')})
        elif self.hour:
            raise ValidationError({'hour': _(
                'Для данной матрицы не нужен час, это бронь для дня.')})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


@property
def is_booking_admin(self):
    return any((
        self.is_superuser,
        self.has_perm('booking.can_add_item'),
        self.has_perm('booking.can_add_itemset'),
        self.has_perm('booking.can_add_itemreserve'),
        self.has_perm('booking.can_change_item'),
        self.has_perm('booking.can_change_itemset'),
        self.has_perm('booking.can_change_itemreserve'),
    ))


User.add_to_class('is_booking_admin', is_booking_admin)
