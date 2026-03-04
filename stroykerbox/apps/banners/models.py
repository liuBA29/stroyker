from datetime import date

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from constance import config
from colorfield.fields import ColorField
from stroykerbox.apps.utils.validators import validator_svg, url_or_path_validator


BANNER_IMG_TYPE_AS_BG, BANNER_IMG_TYPE_AS_IMG = range(1, 3)
BANNER_IMG_TYPE_CHOICES = (
    (BANNER_IMG_TYPE_AS_BG, _('as background')),
    (BANNER_IMG_TYPE_AS_IMG, _('as image')),
)


class BannerManager(models.Manager):
    def __init__(self, display_urls_key, limit=None):
        super().__init__()
        self.display_urls_key = display_urls_key
        self.limit = limit

    def get_active(self):
        """
        Get active banners.
        """
        today = date.today()
        return self.filter(Q(start_date__lte=today) & (
            Q(end_date__isnull=True) | Q(end_date__gte=today)))

    def get_active_for_url(self, url):
        """
        Get active banners for a specific url.
        """
        qs = self.get_active().filter(
            Q(**{self.display_urls_key: url}) | Q(all_pages=True)).distinct()
        if self.limit:
            qs = qs[:self.limit]
        return qs


class BannerAbstractBase(models.Model):
    name = models.CharField(_('name'), max_length=128)
    image = models.ImageField(
        _('image'), upload_to='bnrs/images', blank=True, null=True)
    svg = models.FileField(
        verbose_name=_('svg image'), upload_to='bnrs/images/svg',
        blank=True, null=True, validators=[validator_svg])
    image_url = models.CharField(_('image target url'), max_length=255,
                                 blank=True, null=True,
                                 validators=[url_or_path_validator],
                                 help_text=_('Target url when the image desplays as a link.'))
    position = models.PositiveSmallIntegerField(_('position'), default=0)

    class Meta:
        abstract = True
        ordering = ['position']
        verbose_name = _('banner')
        verbose_name_plural = _('banners')

    def __str__(self):
        return self.name

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


class BannerAbstract(BannerAbstractBase):
    start_date = models.DateField(
        _('start date of publication'), null=True, blank=True)
    end_date = models.DateField(
        _('end date of publication'), null=True, blank=True, db_index=True)
    advertiser_email = models.EmailField(
        _('advertiser email'), null=True, blank=True)
    renewal_notice_date = models.DateField(
        _('renewal notice date'), null=True, blank=True, editable=False,
        help_text=_('The date the advertiser was last notified of the extension of his banner.'
                    'The value is entered automatically.'))
    clicks_counter = models.PositiveIntegerField(
        _('number of clicks on the banner'), default=0, editable=False)
    views_counter = models.PositiveIntegerField(
        _('number of banner views'), default=0, editable=False)
    all_pages = models.BooleanField(_('show on all pages'), default=False)

    class Meta(BannerAbstractBase.Meta):
        abstract = True


class Banner(BannerAbstract):
    objects = BannerManager('display_urls__url')


class StroykerBanner(BannerAbstract):
    objects = BannerManager('display_urls_stroyker__url',
                            config.STROYKER_BANNERS_LIMIT_FOR_URL)

    class Meta:
        ordering = ['position']
        verbose_name = _('stroyker banner')
        verbose_name_plural = _('stroyker banners')


class BannerDisplayUrlAbstract(models.Model):
    """
    Relative URL of the site page where the banner will be displayed.
    """
    banner = models.ForeignKey(Banner, on_delete=models.CASCADE,
                               related_name='display_urls', verbose_name=_('banner'))
    url = models.CharField(_('relative url'), max_length=256, db_index=True,
                           validators=[RegexValidator(r'^(/([\w=&/?-]+)*)?/$',
                                                      message=_('must start and end with a slash (/)'))])

    def __str__(self):
        return f'url: {self.url}'

    class Meta:
        abstract = True
        unique_together = (('banner', 'url'),)


class BannerDisplayUrl(BannerDisplayUrlAbstract):
    pass


class StroykerBannerDisplayUrl(BannerDisplayUrlAbstract):
    banner = models.ForeignKey(StroykerBanner, on_delete=models.CASCADE,
                               related_name='display_urls_stroyker', verbose_name=_('banner'))


class BannerSet(models.Model):
    """
    A block with a set of several special banners (BannerSetItem model).
    """
    key = models.SlugField('ключ', max_length=70, unique=True,
                           help_text=_('Не нужно изменять это значение - оно '
                                       'используется при отображании в шаблоне!'))
    title = models.CharField(
        'заголовок набора', max_length=255, null=True, blank=True)
    row_type = models.PositiveSmallIntegerField(
        'тип отображения', choices=BANNER_IMG_TYPE_CHOICES, default=BANNER_IMG_TYPE_AS_BG)
    published = models.BooleanField(
        'опубликован', default=True, db_index=True)
    grid_columns = models.PositiveSmallIntegerField(
        'class="grid-colums-VALUE"', default=1)
    grid_columns_sm = models.PositiveSmallIntegerField(
        'class="grid-colums-sm-VALUE"', default=2)
    grid_columns_md = models.PositiveSmallIntegerField(
        'class="grid-colums-md-VALUE"', default=3)
    grid_columns_lg = models.PositiveSmallIntegerField(
        'class="grid-colums-lg-VALUE"', default=5)

    class Meta:
        verbose_name = _('banner set')
        verbose_name_plural = _('banner sets')

    def __str__(self):
        return self.title


BANNERS_PER_LINE_CHOICE = (
    (2, 2),
    (3, 3),
    (4, 4),
    (5, 5),
    (6, 6),
)


class BannerMultirowSet(models.Model):
    """
    https://redmine.fancymedia.ru/issues/7055

    Задача взамен блока с двойными/тройными баннерами сделано новый универсальный блок
    текущие наборы баннеров оставляем в том виде, в котором есть, т.к. они используются на проектах

    как должно работать:

    - добавляем набор баннеров

    - у него есть название / ключ (который для вывода будет использоваться) / признак используемой сетки (2 или 3 в ряд)
    вызываться они должны в "блоках для главной" по ключу

    - далее в зависимости от выбранной сетки должны добавляться строки
    в каждой строке соответственно по 2 или по 3 элемента

    - для каждой строки задается тип содержимого
    разница этих типов в том, как обрабатывается картинки
    или она фон (тип 1) или она картинка (тип 2)
    это важно для масштабирования картинок
    т.е. в одном ряду должны быть элементы только одного типа чтобы все корректно отображалось

    - далее заполняются элементы в зависимости от типа
    если тип 1: картинка/блок текста/цвет фона/признак "скрывать в адаптиве"
    если тип 2: картинка/блок текста/признак "скрывать в адаптиве"/ссылка с
    картинки/признак "открывать картинку в полный размер" (будет кликабельна)
    """
    key = models.SlugField(_('key'), max_length=70, unique=True,
                           help_text=_('This value is used in the code. Do not touch it!'))
    title = models.CharField(_('block title'), max_length=255)
    banners_per_line = models.PositiveSmallIntegerField(
        _('banners per line'), choices=BANNERS_PER_LINE_CHOICE, default=2)
    rowsets = models.ManyToManyField(
        'BannerRowSet', through='BannerMultirowSetRows', verbose_name=_('row sets'))

    class Meta:
        verbose_name = _('banner multirow set')
        verbose_name_plural = _('banner multirow sets')

    def __str__(self):
        return self.title


class BannerMultirowSetRows(models.Model):
    multirowset = models.ForeignKey(
        BannerMultirowSet, on_delete=models.CASCADE)
    rowset = models.ForeignKey('BannerRowSet', on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField(_('position'), default=0)

    class Meta:
        ordering = ['position']
        verbose_name = _('multirowset rows membership')
        verbose_name_plural = _('multirowset rows memberships')

    def clean(self):
        banner_cnt = self.rowset.rowset_items.count()
        if banner_cnt > self.multirowset.banners_per_line:
            raise ValidationError(_('The RowSet contains more banners '
                                    '(%(banner_cnt)s) than specified in the '
                                    'MultirowSet (%(banners_per_line)s).') % {
                                        'banner_cnt': banner_cnt,
                                        'banners_per_line': self.multirowset.banners_per_line
            })


class BannerRowSet(models.Model):
    """
    https://redmine.fancymedia.ru/issues/7055

    Для каждой строки задается тип содержимого
    разница этих типов в том, как обрабатывается картинки
    или она фон (тип 1) или она картинка (тип 2)
    это важно для масштабирования картинок
    т.е. в одном ряду должны быть элементы только одного типа чтобы все корректно отображалось
    """
    name = models.CharField(_('name'), max_length=128, null=True, blank=True)
    row_type = models.PositiveSmallIntegerField(
        _('row display type'), choices=BANNER_IMG_TYPE_CHOICES, default=BANNER_IMG_TYPE_AS_BG)

    class Meta:
        verbose_name = _('banner row set')
        verbose_name_plural = _('banner row sets')

    def __str__(self):
        return self.name or f'{dict(BANNER_IMG_TYPE_CHOICES)[self.row_type]}: #{self.pk}'


class BannerRowItemAbstract(BannerAbstractBase):
    name = models.CharField(_('name'), max_length=128, null=True, blank=True,
                            help_text=_('Used as an alt for the banner image or as a link '
                                        'title when the banner is a link.'))
    hide_adaptive = models.BooleanField(_('hide in adaptive'), default=False)
    bg_color = ColorField('background color', null=True, blank=True)
    text = models.TextField(_('text content'), blank=True, null=True)
    img_open_full = models.BooleanField(
        _('open image in full size'), default=False)

    class Meta(BannerAbstractBase.Meta):
        abstract = True

    def __str__(self):
        return self.name or f'bannerrow item #{self.pk}'

    def clean(self):
        if self.image and self.svg:
            raise ValidationError(_('You must to upload just one thing: either '
                                    'an image or an SVG file, not both.'))


class BannerRowItem(BannerRowItemAbstract):
    """
    https://redmine.fancymedia.ru/issues/7055

    Заполняются элементы в зависимости от типа (BannerRowSet.rowset.row_type)
    если тип 1: картинка/блок текста/цвет фона/признак "скрывать в адаптиве"
    если тип 2: картинка/блок текста/признак "скрывать в адаптиве"/ссылка с
    картинки/признак "открывать картинку в полный размер" (будет кликабельна)
    """
    rowset = models.ForeignKey(
        BannerRowSet, on_delete=models.CASCADE, related_name='rowset_items')

    class Meta(BannerAbstractBase.Meta):
        verbose_name = _('banner row item')
        verbose_name_plural = _('banner row items')


class BannerSetRowItem(BannerRowItemAbstract):
    """
    Banner as a unit of a set of banners (BannerSet model).
    """
    rowset = models.ForeignKey(
        BannerSet, on_delete=models.CASCADE, related_name='bannerset_items')

    class Meta(BannerAbstractBase.Meta):
        verbose_name = _('bannerset item')
        verbose_name_plural = _('bannerset items')

    def __str__(self):
        return self.name or f'bannerset item #{self.pk}'
