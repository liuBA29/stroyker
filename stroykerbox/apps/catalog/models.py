import re
import datetime
from copy import deepcopy

from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex
from django.db import models, IntegrityError, transaction
from django.db.models.constraints import UniqueConstraint
from django.db.models import Case, When, Q, F
from django.db.models.functions import Coalesce
from django.core.cache import cache
from django.core.exceptions import ValidationError, FieldDoesNotExist
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.html import strip_tags, format_html
from django.utils.text import Truncator
from django.urls import reverse
from django.forms.models import model_to_dict
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.core.validators import MaxValueValidator
from django.apps import apps

from PIL import Image
from constance import config
from mptt.models import MPTTModel, TreeForeignKey, TreeManyToManyField
from ckeditor.fields import RichTextField
from sorl.thumbnail import ImageField
from smart_selects.db_fields import ChainedManyToManyField
from uuslug import uuslug

from django.conf import settings
from stroykerbox.apps.locations.models import Location
from stroykerbox.apps.locations.helpers import LocationModelManager
from stroykerbox.apps.utils.validators import validator_svg
from stroykerbox.apps.utils.fields import LowerCaseCharField, SlugPreviewField

from .utils import get_dates_prices_for_chart


def model_field_exists(cls, field):
    try:
        cls._meta.get_field(field)
        return True
    except FieldDoesNotExist:
        return False


models.Model.field_exists = classmethod(model_field_exists)


class Category(MPTTModel):
    """
    Category model.
    """

    name = models.CharField(_('name'), max_length=70, help_text=_('Name of category.'))
    parent = TreeForeignKey(
        'self',
        verbose_name=_('parent'),
        null=True,
        blank=True,
        related_name='children',
        db_index=True,
        on_delete=models.SET_NULL,
        help_text=_('Parent category (if any).'),
    )
    image = ImageField(
        _('image'),
        upload_to='categories/images',
        blank=True,
        null=True,
        help_text=_('Category image.'),
    )
    svg_image = models.FileField(
        verbose_name=_('svg image'),
        upload_to='categories/images',
        blank=True,
        null=True,
        validators=[validator_svg],
    )
    slug = models.SlugField(_('slug'), help_text=_('URL-key'))
    published = models.BooleanField(
        _('show on the site'),
        db_index=True,
        default=True,
        help_text=_('Category visibility status flag.'),
    )
    icon = models.FileField(
        verbose_name=_('icon in rubrics'),
        upload_to='categories/images/icons',
        blank=True,
        null=True,
        help_text=_('The category icon to display on category list pages.'),
    )
    updated = models.DateTimeField(_('updated'), auto_now=timezone.now())
    seo_text = RichTextField(
        _('seo text'),
        blank=True,
        null=True,
        help_text=_(
            'Formatted and optimized text to attract the attention of search engines.'
        ),
    )
    is_container = models.BooleanField(
        _('is container'),
        default=False,
        help_text=_('The category is a container for child categories.'),
    )
    list_as_rows = models.BooleanField(
        _('show list as rows'),
        default=False,
        help_text=_(
            'Display a list of products of the category as rows. '
            'Otherwise, a products will be displayed as tiles.'
        ),
    )
    highlight = models.BooleanField(
        _('highlight this category'),
        default=False,
        help_text=_('A flag indicating whether to highlight a category.'),
    )

    related_categories = TreeManyToManyField(
        'self', verbose_name=_('related categories'), blank=True
    )
    maybeinterested_block = models.BooleanField(
        _('show "you may be interested" block'), default=False
    )
    online_discount = models.PositiveSmallIntegerField(
        'online price discount',
        null=True,
        blank=True,
        validators=[MaxValueValidator(100)],
        help_text=_(
            'Percentage discount for the category product price when buying it through the cart.'
        ),
    )
    sidebar_siblings = models.BooleanField(
        _('show siblings in sidebar'),
        default=False,
        help_text=_(
            'Instead of filters, display '
            'links to sibling categories in the '
            'sidebar on the category page.'
        ),
    )
    products_per_row = models.PositiveSmallIntegerField(
        _('кол-во товаров на строку'),
        null=True,
        blank=True,
        help_text=_('Кол-во товаров в строке на ' 'странице категории.'),
    )
    vk_group_id = models.PositiveIntegerField(
        _('vk-market group ID'),
        null=True,
        blank=True,
        help_text=_('ID группы товаров в VK.'),
    )

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=['slug', 'level', 'parent'], name='unique_with_optional_parent'
            ),
            UniqueConstraint(
                fields=['slug', 'level'],
                condition=Q(parent=None),
                name='unique_without_optional_parent',
            ),
        ]
        verbose_name = _('category')
        verbose_name_plural = _('categories')

    def __str__(self):
        return f'{self.name}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuslug(self.name, instance=self)

        self.full_clean()

        if not self.parent:
            self.level = 0
        try:
            with transaction.atomic():
                super().save(*args, **kwargs)
        except IntegrityError:
            self.slug = uuslug(self.name, instance=self)
            self.save()

    @property
    def has_seo_text(self) -> bool:
        if self.seo_text:
            return True
        try:
            return (
                apps.get_model('seo.MetaTag')
                .objects.filter(url=self.get_absolute_url(), seo_text__isnull=False)
                .exists()
            )
        except Exception:
            pass
        return False

    @property
    def published_children(self):
        return self.children.filter(published=True)

    @cached_property
    def online_price_discount(self):
        if self.online_discount:
            return self.online_discount
        elif self.parent and self.parent.online_discount:
            return self.parent.online_discount

        return config.PRODUCT_ONLINE_PRICE_DISCOUNT

    def clean(self):
        if self.image and self.svg_image:
            raise ValidationError(
                _(
                    'You must to upload just one thing: either '
                    'an image or an SVG file, not both.'
                )
            )

    def get_absolute_url(self):
        if self.parent:
            return reverse('catalog:subcategory', args=(self.parent.slug, self.slug))
        else:
            return reverse('catalog:category', args=(self.slug,))

    @property
    def image_file(self):
        return self.image or self.svg_image

    def get_first_ancestor_with_filters(self):
        for category in self.get_ancestors(ascending=True, include_self=True):
            if category.categoryparametermembership_set.exists():
                return category

    def get_descendant_products(self):
        qs = Product.objects.published().filter(
            categories__in=self.get_descendants(include_self=True)
        )
        if config.PRODUCT_ONLY_AVAIL_BY_DEFAULT:
            qs = qs.filter(stocks_availability__available__gt=0)
        return qs.distinct()

    def get_descendant_products_price_agg(self, location=None):
        if Location.check_default(location):
            qs = self.get_descendant_products()
        else:
            qs = ProductLocationPrice.objects.filter(
                location=location, product__in=self.get_descendant_products()
            )
        return qs.aggregate(models.Min('price'), models.Max('price'))

    def get_descendant_products_count(self):
        return self.get_descendant_products().count()

    def get_published_children(self):
        return Category.objects.filter(parent=self, published=True)

    def get_min_product_price(self):
        return self.get_descendant_products().aggregate(models.Min('price'))[
            'price__min'
        ]

    @property
    def get_category_paremeters(self):
        """
        Getting a set of parameters for a specific category.
        """
        params = (
            self.categoryparametermembership_set.select_related('parameter')
            .filter(display=True)
            .order_by('position', 'parameter__name')
        )
        if config.CATALOG_SHOW_CHILDS_IN_PARENT:
            allowed_categories = [self] + list(self.get_published_children())
            allowed_params = CategoryParameterMembership.objects.filter(
                category__in=allowed_categories, display=True
            ).values_list('parameter__name', flat=True)
            params = params.exclude(~models.Q(parameter__name__in=allowed_params))

        return ((cmp.parameter, cmp.expanded) for cmp in params)

    @staticmethod
    def autocomplete_search_fields():
        return ('name__icontains',)

    @property
    def is_root(self):
        return self.is_root_node()


class ProductLocationPrice(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    product = models.ForeignKey(
        'Product', on_delete=models.CASCADE, related_name='location_prices'
    )
    price = models.DecimalField(
        _('price'),
        max_digits=12,
        decimal_places=2,
        db_index=True,
        null=True,
        blank=True,
    )
    old_price = models.DecimalField(
        _('old price'),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
    )
    purchase_price = models.DecimalField(
        _('purchase price'),
        max_digits=12,
        decimal_places=2,
        db_index=True,
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(_('update date'), auto_now=True)

    class Meta:
        unique_together = (('location', 'product'),)
        verbose_name = _('location price')
        verbose_name_plural = _('location prices')

    @cached_property
    def currency_price(self):
        if not self.price:
            return 0
        return self.price * self.product.currency_rate

    @cached_property
    def currency_old_price(self):
        if not self.old_price:
            return 0
        return self.old_price * self.product.currency_rate

    @cached_property
    def currency_purchase_price(self):
        if not self.purchase_price:
            return 0
        return self.purchase_price * self.product.currency_rate


class ProductRelatedManager(models.Manager):
    def get_queryset(self):
        return ProductRelatedQuerySet(self.model)


class ProductManager(models.Manager):
    def get_queryset(self):
        return ProductQuerySet(self.model)

    def published(self):
        return (
            self.prefetch_related('images', 'categories')
            .filter(published=True)
            .exclude(slug='')
        )


class ProductRelatedQuerySet(models.query.QuerySet):
    def exclude_by_modification_code(self, order_by_priority=True):
        if not config.PRODUCTS_MERGE_BY_MODIFICATION_CODE:
            return self
        exclude_pks = []
        exclude_code = set()
        products_qs = self.filter(
            product__published=True, product__modification_code__isnull=False
        ).exclude(product__modification_code='')

        # https://redmine.fancymedia.ru/issues/12233
        if order_by_priority:
            products_qs = products_qs.order_by('-product__is_mod_priority')
        else:
            products_qs = products_qs.order_by()

        for pk, code in products_qs.values_list(
            'product__pk', 'product__modification_code'
        ):
            if code not in exclude_code:
                exclude_code.add(code)
            else:
                exclude_pks.append(pk)
        return self.exclude(pk__in=exclude_pks)


class ProductQuerySet(models.query.QuerySet):
    def apply_form_filter(self, form):
        """
        Apply form filter to the query set
        """
        # search for filter parameters in get dict
        result = self
        for field in form:
            value = form[field.name].value()
            if value and all(value):
                try:
                    parameter = Parameter.objects.get(input_name=field.name)
                    if parameter.widget == 'radio':
                        result = result.filter(
                            productparametermembership__parameter=parameter,
                            productparametermembership__value_slug=value,
                        )
                    elif parameter.widget == 'dimensions':
                        result = result.filter(
                            productparametermembership__parameter=parameter
                        )
                        _result = deepcopy(result)
                        excluded_items = []
                        # convert values list to int
                        value = [int(x) for x in value]
                        for product in _result:
                            param = product.productparametermembership_set.filter(
                                parameter=parameter
                            )[0]
                            dimensions = [
                                int(x)
                                for x in re.sub(r'\D', 'x', param.value_slug).split('x')
                            ]
                            if len(dimensions) != 3:
                                # incorrect dimensions parameter value (example: 120x80x150)
                                continue
                            # check dimensions ranges
                            if not (
                                value[0] <= dimensions[0] <= value[1]
                                and value[2] <= dimensions[1] <= value[3]
                                and value[4] <= dimensions[2] <= value[5]
                            ):
                                excluded_items.append(product.pk)
                        if excluded_items:
                            # exclude items which don't fit requested dimensions
                            result = result.exclude(pk__in=excluded_items)
                    elif parameter.widget == 'range':
                        result = result.filter(
                            productparametermembership__parameter=parameter,
                            productparametermembership__value_int__range=value,
                        )
                    else:
                        # if 'checkbox' or any other
                        result = result.filter(
                            productparametermembership__parameter=parameter,
                            productparametermembership__value_slug__in=value,
                        )
                except Parameter.DoesNotExist:
                    # apply hardcoded parameters
                    if field.name == 'price':
                        result = result.filter(price__range=value)
                    elif field.name == 'brands':
                        result = result.filter(brand__slug__in=value)
                    elif field.name == 'extra':
                        if value == 'discount':
                            result = result.filter(discount=True)
                        elif value == 'novelties':
                            result = result.filter(novelty=True)
        return result

    def exclude_by_modification_code(self, order_by_priority=True):
        if not config.PRODUCTS_MERGE_BY_MODIFICATION_CODE:
            return self
        exclude_pks = []
        exclude_code = set()
        products_qs = self.filter(
            published=True, modification_code__isnull=False
        ).exclude(modification_code='')

        # https://redmine.fancymedia.ru/issues/12233
        if order_by_priority:
            products_qs = products_qs.order_by('-is_mod_priority')
        else:
            products_qs = products_qs.order_by()
        for pk, code in products_qs.values_list('pk', 'modification_code'):
            if code not in exclude_code:
                exclude_code.add(code)
            else:
                exclude_pks.append(pk)
        return self.exclude(pk__in=exclude_pks)

    def catalog_order(self):
        output = self.annotate(
            available_img=Case(
                When(images__isnull=False, then=1),
                default=0,
                output_field=models.IntegerField(),
            ),
            available=Coalesce(
                models.Sum('stocks_availability__available'),
                0,
                output_field=models.FloatField(),
            ),
            # https://redmine.nastroyker.ru/issues/16909
            price_value=Case(
                When(price__isnull=True, then=99999999),
                default=F('price'),
                output_field=models.IntegerField(),
            ),
        )
        return output.order_by(
            'position', '-available', 'price_value', 'available_img', '-updated_at'
        )


class Product(models.Model):
    name = models.CharField(_('name'), max_length=256, help_text=_('Product Name'))
    sku = models.CharField(
        _('commodity item identifier'),
        max_length=128,
        unique=True,
        help_text=_('Unique identifier for the product.'),
    )
    third_party_code = models.CharField(
        _('third-party system code'), max_length=128, blank=True, null=True
    )
    slug = models.SlugField(_('slug'), unique=True, max_length=256)
    categories = TreeManyToManyField(
        'Category',
        verbose_name=_('categories'),
        related_name='products',
        help_text=(
            'Список категорий товара. '
            'При создании/обновлении через API нужно передавать список(массив) из ID нужных категорий.'
        ),
    )
    published = models.BooleanField(
        _('show on site'),
        db_index=True,
        default=False,
        help_text=_('Product visibility status flag.'),
    )
    price = models.DecimalField(
        _('price'),
        max_digits=12,
        decimal_places=2,
        db_index=True,
        null=True,
        blank=True,
        help_text=_('The main price of the product.'),
    )
    price_from = models.BooleanField(
        _('price "from"'),
        default=False,
        help_text=_('Отображать цену товара с признаком "от".'),
    )
    price_from_to = models.BooleanField(
        _('цена "от... до"'),
        default=False,
        help_text=_('Отображать цену товара с признаком "от... до".'),
    )
    old_price = models.DecimalField(
        _('old price'),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        default=None,
        help_text=_('The old price of the product.'),
    )
    purchase_price = models.DecimalField(
        _('purchase price'),
        max_digits=12,
        decimal_places=2,
        db_index=True,
        null=True,
        blank=True,
        help_text=_('The main purchase price of the product.'),
    )
    price_type = models.ForeignKey(
        'PriceType',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_('price type'),
        help_text=_('Type of product price (target price group).'),
    )
    multiplicity = models.DecimalField(
        _('Multiplicity of packaging'), default=1, decimal_places=5, max_digits=8
    )
    multiplicity_label = models.CharField(
        _('Multiplicity of packaging label'), max_length=32, blank=True, null=True
    )
    days_to_arrive = models.PositiveSmallIntegerField(
        _('days to arrive'),
        null=True,
        blank=True,
        help_text=_(
            'Optional. The number of days through '
            'which the missing product will '
            'arrive at some warehouse.'
        ),
    )
    uom = models.ForeignKey(
        'Uom',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_('unit'),
        help_text=_('Unit of measurement for the product.'),
    )
    is_hit = models.BooleanField(
        _('is bestseller'),
        default=False,
        db_index=True,
        help_text=_('Flag: the product is popular.'),
    )
    is_new = models.BooleanField(
        _('product is new'),
        default=False,
        db_index=True,
        help_text=_('Flag: the product is new.'),
    )
    is_sale = models.BooleanField(
        _('sale'),
        default=False,
        db_index=True,
        help_text=_('Flag: The product is participating in a sale.'),
    )
    discounted = models.BooleanField(
        _('discounted'),
        default=False,
        db_index=True,
        help_text=_('Flag: the product is discounted.'),
    )
    is_action = models.BooleanField(
        _('акция'),
        default=False,
        db_index=True,
        help_text=_('Признак того, что товар участвует в акции.'),
    )
    description = models.TextField(
        _('product description'),
        blank=True,
        null=True,
        help_text=_('Product description.'),
    )
    use_editor = models.BooleanField(
        'использовать редактор',
        default=True,
        help_text=(
            'Использовать визуальный редактор для полей "описание" и "описание 2".'
        ),
    )

    # https://redmine.fancymedia.ru/issues/11434
    description2 = models.TextField(
        _('описание 2'),
        blank=True,
        null=True,
        help_text=_('Дополнительное описание товара.'),
    )

    short_description = models.TextField(_('short description'), blank=True, null=True)
    weight = models.FloatField(
        _('product weight, kg'), default=0, help_text=_('Product weight (in kg).')
    )
    volume = models.FloatField(
        _('product volume, m3'),
        blank=True,
        null=True,
        help_text=_('Product volume (in m3).'),
    )
    length = models.FloatField(
        _('product length, mm'),
        blank=True,
        null=True,
        help_text=_('Product length (in mm).'),
    )
    width = models.FloatField(
        _('product width, mm'),
        blank=True,
        null=True,
        help_text=_('Product width (in mm).'),
    )
    height = models.FloatField(
        _('product height, mm'),
        blank=True,
        null=True,
        help_text=_('Product height (in mm).'),
    )
    created_at = models.DateTimeField(_('created date'), auto_now_add=True)
    updated_at = models.DateTimeField(_('update date'), auto_now=True)
    position = models.PositiveIntegerField(_('position'), default=0)
    search_words = models.TextField(_('words to search'), blank=True, null=True)

    # search index
    search_document = SearchVectorField(null=True, blank=True)

    yml_export = models.BooleanField(_('Export to YML'), default=False)
    modification_code = models.CharField(
        'modification code', max_length=32, null=True, blank=True
    )
    vk_market = models.BooleanField(_('use for vk-market'), default=False)
    price_in_compete = models.BooleanField(
        _('цена в "конкуренции"'),
        default=False,
        help_text=_(
            'Цена товара участвует в механизме '
            'конкуренции (проект "Мониторинг"). '
            'Т.е., заморожена от изменений, в том '
            'числе не меняется при подсчете онлайн-цены.'
        ),
    )
    currency = models.ForeignKey(
        'Currency',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_('валюта'),
    )
    related_products = models.ManyToManyField(
        'self', through='ProductRelated', through_fields=('ref', 'product')
    )
    is_mod_priority = models.BooleanField(
        'приоритет в модификациях',
        default=False,
        help_text='Выводить в кач-ве приоритетного, если товары склеены.',
    )

    objects = ProductManager()

    @cached_property
    def multiplicity_label_suffix(self):
        if self.multiplicity_label:
            return f'/{self.multiplicity_label}'
        return self.uom_suffix

    @cached_property
    def uom_suffix(self):
        if self.uom:
            return f'/{self.uom}'
        return ''

    @cached_property
    def has_calc_related_products(self):
        if config.RELATED_PRODUCTS_DISPLAY_VARIANT == 'calculator':
            return Product.objects.published().filter(related__ref=self).exists()

    @cached_property
    def has_related_products(self):
        return Product.objects.published().filter(related__ref=self).exists()

    def get_final_price(self, user, location):
        product_price = getattr(
            self.location_price_object(location), 'currency_price', None
        )
        final_price = product_price

        if user.is_authenticated:
            personal_price = self.personal_price(user, location)
            if personal_price and personal_price < final_price:
                final_price = personal_price

        online_price = self.online_price(user, location)
        try:
            # на случай, если в final_price придет не цифра
            if online_price and online_price < final_price:
                return online_price
        except TypeError:
            pass
        return final_price

    @cached_property
    def has_price_from_to(self):
        return all((self.price_from_to, self.price, self.old_price))

    @cached_property
    def modifications(self):
        return Product.objects.filter(
            modification_code=self.modification_code, published=True
        ).exclude(
            models.Q(modification_code__isnull=True) | models.Q(modification_code='')
        )

    class Meta:
        verbose_name = _('product')
        verbose_name_plural = _('products')
        ordering = ['position', 'price', '-updated_at']
        indexes = [GinIndex(fields=['search_document'])]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_price = self.price
        self._original_price_in_compete = self.price_in_compete

    def __str__(self):
        return self.name

    def check_slug(self, save=True):
        if self.slug:
            return
        self.slug = uuslug(self.name, instance=self)
        if save:
            self.save(update_fields=('slug',))

    def save(self, *args, **kwargs):
        if not kwargs.pop('force', None) and (
            self.price_in_compete
            and self._original_price_in_compete
            and self._original_price != self.price
        ):
            self.price = self._original_price

        self.check_slug(save=False)
        return super().save(*args, **kwargs)

    @cached_property
    def currency_rate(self):
        if self.currency:
            return self.currency.rate
        return 1

    @cached_property
    def currency_price(self):
        if not self.price:
            return 0
        return self.price * self.currency_rate

    @cached_property
    def currency_old_price(self):
        if not self.old_price:
            return 0
        return self.old_price * self.currency_rate

    @cached_property
    def currency_purchase_price(self):
        if not self.purchase_price:
            return 0
        return self.purchase_price * self.currency_rate

    @property
    def category(self):
        return self.categories.first()

    def index_components(self):
        """
        Returns the weight and value of the fields to be entered in the search index (search_document field).
        This method will be called when the product is saved (by signal) to update the search index.
        """
        return {
            'A': self.name,
            'B': self.sku,
            'C': self.search_words,
        }

    def get_absolute_url(self):
        if not self.slug:
            return ''
        return reverse('catalog:product_view', args=(self.slug,))

    @property
    def code(self):
        return getattr(self, config.PRODUCT_CODE_FIELD, self.sku) or ''

    @property
    def as_dict(self):
        result = model_to_dict(self, exclude=('description',))
        result['uom'] = self.uom.name if self.uom else '-'
        result['code'] = self.code
        return result

    @cached_property
    def _images_all(self):
        return self.images.all()

    @cached_property
    def main_image(self):
        try:
            return self._images_all[0]
        except IndexError:
            pass

    @property
    def main_image_second(self):
        try:
            return self._images_all[1]
        except IndexError:
            pass

    def is_available(self, location=None):
        if not getattr(self.location_price_object(location), 'price', None):
            return
        return (
            self.available_items_count(location) > 0
            or config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE
        )

    def get_short_description(self):
        if self.short_description:
            return self.short_description
        text = strip_tags(self.description)
        return Truncator(text).words(15, truncate='...', html=True)

    def get_related_products(self):
        return ProductRelated.objects.filter(ref=self.object, product__published=True)

    @staticmethod
    def autocomplete_search_fields():
        return ('name__icontains',)

    @property
    def available_stocks_list(self):
        return [
            o.warehouse
            for o in ProductStockAvailability.objects.filter(
                product=self, available__gt=0
            ).only('warehouse')
        ]

    def availability_by_stocks(self, location=None):
        qs = ProductStockAvailability.objects.filter(product=self)
        default_location = Location.get_default_location()

        if location and location.id != default_location.id:
            qs = qs.filter(warehouse__location=location)
        else:
            qs = qs.filter(
                models.Q(warehouse__location__isnull=True)
                | models.Q(warehouse__location=default_location)
            )

        return qs

    def available_items_count(self, location=None):
        """
        Get the number of items of this product left
        in stores in the default location or by location if provided.
        """
        qs = self.availability_by_stocks(location)
        sum = qs.aggregate(models.Sum('available')).get('available__sum', 0) or 0
        try:
            if sum.is_integer():
                return int(sum)
        except AttributeError:
            pass

        return sum

    def availability_count_or_status(self, location=None):
        sum = self.available_items_count(location)
        return sum if sum > 0 else self.availability_status(location)

    def availability_status(self, location=None):
        if self.available_items_count(location) <= 0:
            return config.PRODUCT_NOT_AVAIBLE_STATUS_NAME
        return self.get_availability_status_name()

    def get_availability_status_name(self, location=None):
        count = self.available_items_count(location)
        try:
            status = ProductAvailabilityStatus.objects.values_list(
                'name', flat=True
            ).get(range_from__lte=count, range_to__gte=count)
        except ProductAvailabilityStatus.DoesNotExist:
            return count
        except ProductAvailabilityStatus.MultipleObjectsReturned:
            return (
                ProductAvailabilityStatus.objects.values_list('name', flat=True)
                .filter(range_from__lte=count, range_to__gte=count)
                .last()
            )
        return status

    def online_price(self, user=None, location=None, **kwargs):
        if self.price_in_compete:
            return

        main_category = kwargs.get('category') or self.category

        if main_category:
            discount = main_category.online_price_discount
        else:
            discount = config.PRODUCT_ONLINE_PRICE_DISCOUNT

        if not discount or discount <= 0:
            return

        price_object = self.location_price_object(location)

        if price_object and getattr(price_object, 'price', False):
            currency_price = price_object.currency_price
            price = currency_price - (currency_price / 100 * discount)
            return price

    def personal_price(self, user=None, location=None):
        """
        The personal price is applied if the user is a member of one of
        the discount groups and the product has a purchase price.
        """
        price_object = self.location_price_object(location)
        price = price_object.currency_price
        if price_object:
            if user and user.is_authenticated:
                discount = None
                calculation = None
                if user.discount:
                    discount = user.discount
                    calculation = user.calculation
                elif user.discount_group and user.discount_group.discount:
                    discount = user.discount_group.discount
                    calculation = user.discount_group.calculation
                if discount:
                    if calculation == 'discount':
                        price = (
                            price_object.currency_price
                            - price_object.currency_price / 100 * discount
                        )
                    elif price_object.purchase_price and calculation == 'extra_charge':
                        price = (
                            price_object.purchase_price
                            + price_object.purchase_price / 100 * discount
                        )
            return price

    def get_history_prices(self, choiced_period='month', location=None):

        today = timezone.datetime.today().date()

        if choiced_period == 'month':
            period = models.Q(
                created__range=[today - datetime.timedelta(days=30), today]
            )
        elif choiced_period == 'year':
            period = models.Q(
                created__range=[today - datetime.timedelta(days=365), today]
            )
        elif choiced_period == 'quarter':
            period = models.Q(
                created__range=[today - datetime.timedelta(days=90), today]
            )
        elif choiced_period == 'all_time':
            period = models.Q()

        location_is_default = Location.check_default(location)

        location_q = models.Q()
        if not location_is_default:
            location_q = models.Q(location_id=location.id)

        # prices_data_qs = prices_data_qs.filter(location_id=location.id)
        prices_data = (
            self.history_prices.filter(period & location_q)
            .values_list('created', 'price')
            .order_by('created')
        )

        if not prices_data.exists():
            # If there are no records for the required period,
            # then we take the latest one for the chart.
            last_entry = (
                self.history_prices.filter(location_q)
                .values_list('created', 'price')
                .order_by('created')
                .last()
            )
            prices_data = [last_entry]

        if prices_data:
            try:
                dates, prices = get_dates_prices_for_chart(prices_data)
            except TypeError:
                return

            return {'dates': dates, 'prices': prices} if prices else None

    @cached_property
    def use_floatprice(self):
        return all(
            (config.FLOATPRICE_IS_ACTIVE, hasattr(self, 'floatprice'), self.price)
        )

    def location_price_object(self, location=None):
        if self.use_floatprice:
            return self.floatprice
        if not Location.check_default(location):
            try:
                return ProductLocationPrice.objects.get(product=self, location=location)
            except ProductLocationPrice.DoesNotExist:
                pass
        return self


class ProductImage(models.Model):
    """
    Product's image
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='images'
    )
    image = ImageField(_('image'), upload_to='products/images', max_length=256)
    position = models.PositiveSmallIntegerField(_('position'), default=0)
    has_watermarked = models.BooleanField(default=False, editable=False)
    image_file_size = models.IntegerField(editable=False, null=True, blank=True)

    class Meta:
        ordering = ['position', 'id']
        verbose_name = _('product image')
        verbose_name_plural = _('product images')

    def update_file_size_value(self):
        if not self.image:
            return
        self.image_file_size = self.image.file.size
        self.save(update_fields=('image_file_size',))

    @cached_property
    def max_image_size_limit(self) -> int:
        """
        Возвращает лимит в байтах.
        https://redmine.nastroyker.ru/issues/17661
        """
        return config.ADMIN_PRODUCT_IMG_MAX_SIZE_MB * (1024 * 1024)  # mb to bytes

    def clean(self):
        if not self.image:
            return
        image_size_limit = self.max_image_size_limit
        # https://redmine.nastroyker.ru/issues/17661#note-3
        try:
            if image_size_limit > 0 and self.image.file.size > image_size_limit:
                raise ValidationError(
                    (
                        f'Максимальных размер файла изображения не должен превышать {image_size_limit} байт. '
                        f'Изображение {self.image.file.name} имеет размер {self.image.file.size} байт.'
                    )
                )
        # на случай физического отсутствия файла на сервере
        except FileNotFoundError:
            pass

    def save(self, *args, **kwargs):
        # set the position for newly created images,
        # if a nonzero position is not already set
        self.full_clean()
        if not self.pk and not self.position:
            last_index_qs = self.__class__.objects.filter(product_id=self.product.id)
            if last_index_qs.exists():
                self.position = (
                    last_index_qs.aggregate(models.Max('position'))['position__max'] + 1
                )
        if self.image:
            self.image_file_size = self.image.file.size
        else:
            self.image_file_size = 0
        super().save(*args, **kwargs)

    def resize_image(self, max_width):
        fp = self.image.path
        with Image.open(fp) as img:
            output_size = None
            if img.width > max_width:
                height = int(img.height * max_width / img.width)
                output_size = max_width, height
            elif img.height > max_width:
                width = int(img.width * max_width / img.height)
                output_size = width, max_width

            if output_size:
                img.thumbnail(output_size, Image.Resampling.LANCZOS)
                img.save(fp)
                return True


class ProductCertificate(models.Model):
    """
    Certificates for the product (images or file)
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='certificates'
    )
    name = models.CharField(_('name'), max_length=255)
    file = models.FileField(
        _('file'),
        upload_to='product/certificates',  # noqa: ignore=B001
        help_text=_('Select image or document'),
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    def __str__(self):
        return str(self.name)

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('product certificate')
        verbose_name_plural = _('product certificates')

    def is_image(self):
        img = ('BMP', 'JPEG', 'GIF', 'JPG', 'JPE', 'PNG', 'TIFF', 'TIF')
        filename = str(self.file).upper()
        return filename.endswith(img)

    @property
    def file_extension(self):
        if self.file:
            from pathlib import Path

            return Path(self.file.url).suffix[1:4]
        return ''

    @property
    def file_size(self):
        """
        This will return the file size converted
        from bytes to MB... GB... etc
        """
        if self.file:
            try:
                file_size = self.file.size
                if file_size < 512000:
                    file_size /= 1024.0
                    ext = _('Kb')
                elif file_size < 4194304000:
                    file_size /= 1048576.0
                    ext = _('Mb')
                else:
                    file_size /= 1073741824.0
                    ext = _('Gb')
                return '%s %s' % (str(round(file_size, 1)), ext)
            except Exception:
                pass
        return ''


class ProductProps(models.Model):
    product = models.ForeignKey(Product, related_name='props', on_delete=models.CASCADE)
    name = models.CharField(
        _('name'),
        max_length=255,
    )
    slug = models.SlugField(
        _('slug'),
        max_length=255,
    )
    value = models.TextField(_('value'))
    position = models.PositiveSmallIntegerField(_('position'), default=0)

    class Meta:
        unique_together = (('product', 'slug'),)
        verbose_name = _('product property')
        verbose_name_plural = _('product properties')
        ordering = ['position']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuslug(self.name, instance=self)
        super().save(*args, **kwargs)


class ProductRelated(models.Model):
    product = models.ForeignKey(
        Product,
        related_name='related',
        on_delete=models.CASCADE,
        verbose_name=_('related product'),
    )
    ref = models.ForeignKey(
        Product, related_name='ref', on_delete=models.CASCADE, verbose_name=_('product')
    )
    position = models.PositiveIntegerField(_('position'), default=0)

    objects = ProductRelatedManager()

    class Meta:
        verbose_name = _('related product')
        verbose_name_plural = _('related products')
        ordering = ['position']


class Parameter(models.Model):
    WIDGET_CHOICES = (
        ('radio', _('radiobutton')),
        ('checkbox', _('checkbox')),
        ('select', _('drop-down list')),
        ('range', _('range')),
    )
    DATA_TYPE_CHOICES = (('decimal', _('number')), ('str', _('string')))
    MODE_WIDGET_BUTTON, MODE_WIDGET_SELECT = 'button', 'select'
    MODE_WIDGET_CHOICES = (
        (MODE_WIDGET_BUTTON, _('button')),
        (MODE_WIDGET_SELECT, _('select')),
    )

    name = models.CharField('имя', max_length=255, db_index=True)
    slug = models.SlugField(unique=True)
    data_type = models.CharField(
        _('type'), max_length=7, default='str', choices=DATA_TYPE_CHOICES
    )
    widget = models.CharField(
        _('widget'), max_length=10, default='checkbox', choices=WIDGET_CHOICES
    )
    position = models.PositiveIntegerField(_('position'), default=0)
    use_for_modes = models.BooleanField(
        _('use for modifications'),
        default=False,
        help_text=_('Use as product modification property.'),
    )
    mode_widget = models.CharField(
        _('modification widget'),
        help_text=_('Widget for displaying in product modifications.'),
        max_length=6,
        default=MODE_WIDGET_BUTTON,
        choices=MODE_WIDGET_CHOICES,
    )

    class Meta:
        ordering = ('position', 'name')
        verbose_name = _('parameter')
        verbose_name_plural = _('parameters')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuslug(self.name, instance=self)

        if self.widget == 'range' and 'decimal' in dict(self.DATA_TYPE_CHOICES):
            self.data_type = 'decimal'

        super().save(*args, **kwargs)

    def get_parameter_choices_cache_key(
        self, category, partner_id, include_subcategories
    ):
        return 'parameter_choices_{}_{}_{}'.format(
            category.pk, self.pk, include_subcategories
        )

    def get_parameter_choices(
        self, category, partner_id=None, include_subcategories=True, use_cache=False
    ):
        """
        Get list of choices for the current parameter and given category.
        """
        if use_cache:
            cached_result = cache.get(
                self.get_parameter_choices_cache_key(
                    category, partner_id, include_subcategories
                )
            )
            if cached_result is not None:
                return cached_result

        product_parameters = ProductParameterValueMembership.objects.prefetch_related(
            'parameter_value'
        ).filter(parameter=self)
        if partner_id:
            product_parameters = product_parameters.filter(
                product__partner_product__partner_id=partner_id,
                product__partner_product__published=True,
            )
        else:
            product_parameters = product_parameters.filter(product__published=True)

        if include_subcategories:
            # Include parameter values for products from all subcategories.
            product_parameters = product_parameters.filter(
                product__categories__in=category.get_descendants(include_self=True)
            )
        else:
            product_parameters = product_parameters.filter(
                product__in=category.products.filter(published=True)
            )

        if config.PRODUCT_ONLY_AVAIL_BY_DEFAULT:
            product_parameters = product_parameters.filter(
                product__stocks_availability__available__gt=0
            )

        if self.data_type == 'str':
            key_field = 'parameter_value__value_slug'
            value_field = 'parameter_value__value_str'
            choices = (
                product_parameters.order_by('parameter_value__position', key_field)
                .values_list(key_field, value_field)
                .distinct()
                .annotate(products_count=models.Count('product', distinct=True))
            )
        else:
            param_decimal = (
                product_parameters.order_by('value_decimal')
                .values_list('value_decimal', 'value_decimal')
                .distinct()
                .annotate(products_count=models.Count('product', distinct=True))
            )

            choices = tuple(param_decimal)

        # Put the products count into the label if the count is available.
        # if len(choices) > 2:
        choices = [
            (
                choice[0],
                (
                    format_html('{} <span>{}</span>', choice[1], choice[2])
                    if len(choice) == 3
                    else choice[1]
                ),
            )
            for choice in choices
            if choice[0]
        ]
        return choices


class ParameterValue(models.Model):
    """
    Parameter value model.
    """

    parameter = models.ForeignKey(
        Parameter, related_name='values', on_delete=models.CASCADE
    )
    value_str = models.CharField(
        _('value'), max_length=255, db_index=True, blank=True, default=''
    )
    value_slug = models.SlugField(_('slug'), blank=True)
    seo_str = models.CharField(
        _('alternative value (seo)'), max_length=255, null=True, blank=True
    )
    position = models.PositiveSmallIntegerField(_('position'), default=0)

    def clean(self):
        # validate value_str field
        if self.parameter.data_type == 'str':
            if len(self.value_str) == 0:
                raise ValidationError(_('The string cannot be empty'))
            # validate value_slug field
            if len(self.value_slug) == 0:
                raise ValidationError(_('The slug value cannot be empty'))
        elif self.value_str or self.value_slug:
            raise ValidationError(
                _('Numeric parameter cannot contain string characters')
            )

    def save(self, *args, **kwargs):
        if not self.value_slug and self.value_str:
            self.value_slug = uuslug(
                self.value_str, instance=self, slug_field='value_slug'
            )

        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.parameter} - {self.value_str}'

    class Meta:
        ordering = ['position', 'value_str']
        unique_together = (('parameter', 'value_str'),)
        verbose_name = _('parameter value')
        verbose_name_plural = _('parameter values')


class ProductParameterValueMembership(models.Model):
    """
    Product parameter value
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='params'
    )
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    # values see: https://github.com/digi604/django-smart-selects docs
    parameter_value = ChainedManyToManyField(
        ParameterValue,
        chained_field='parameter',
        chained_model_field='parameter',
        blank=True,
        related_name='parameter_values',
    )
    value_decimal = models.DecimalField(
        _('numerical value'), max_digits=8, decimal_places=2, null=True, blank=True
    )
    comment = models.TextField(_('comment'), blank=True, default='')
    position = models.PositiveSmallIntegerField(_('position'), default=0)

    @property
    def value(self):
        if self.value_decimal:
            values = self.value_decimal.normalize()
        else:
            values = ', '.join(
                p.value_str for p in self.parameter_value.order_by('position')
            )
        return values

    def clean(self):
        if not hasattr(self, 'parameter') or self.parameter is None:
            raise ValidationError(_('You must select a parameter'))
        if self.parameter.data_type == 'decimal' and not self.value_decimal:
            raise ValidationError(_('Range values required'))

    def save(self, *args, **kwargs):
        if self.product.category:
            # Create a reference for the current parameter in a category if it does not exist.
            CategoryParameterMembership.objects.get_or_create(
                category=self.product.category,
                parameter=self.parameter,
                defaults={
                    'position': self.product.category.categoryparametermembership_set.count()
                },
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return '{} - {}'.format(self.product, self.parameter)

    class Meta:
        unique_together = (('product', 'parameter'),)
        verbose_name = _('product parameter value')
        verbose_name_plural = _('product parameter values')
        ordering = ['position']


class CategoryParameterMembership(models.Model):
    """
    Category parameter
    """

    category = TreeForeignKey(Category, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    position = models.PositiveSmallIntegerField(_('position'), db_index=True)
    display = models.BooleanField(default=False)
    expanded = models.BooleanField(default=False)

    class Meta:
        index_together = (('category', 'parameter', 'display'),)
        unique_together = (('category', 'parameter'),)
        ordering = ['position']
        verbose_name = _('category parameter')
        verbose_name_plural = _('category parameters')

    def __str__(self):
        return '{} - {}'.format(self.category.name, self.parameter.name)

    def get_category_parameter_choices(self):
        """
        Get list of choices for the current parameter and category
        """
        key_field = (
            'parameter_value__value_slug'
            if self.parameter.data_type == 'str'
            else 'value_decimal'
        )
        value_field = (
            'parameter_value__value_str'
            if self.parameter.data_type == 'str'
            else 'value_decimal'
        )
        return (
            ProductParameterValueMembership.objects.filter(
                product__category__in=self.category.get_descendants(
                    include_self=True
                ).all(),
                product__published=True,
                parameter=self.parameter,
            )
            .values_list(key_field, value_field)
            .order_by('parameter_value__position', value_field)
            .distinct()
        )


class CatalogDictItemAbstract(models.Model):
    name = models.CharField(_('name'), max_length=32, help_text=_('Name'))
    description = models.CharField(
        _('description'),
        max_length=255,
        blank=True,
        null=True,
        help_text=_('Description'),
    )

    class Meta:
        abstract = True
        ordering = ('name',)

    def __str__(self):
        return self.name


class Uom(CatalogDictItemAbstract):
    class Meta:
        verbose_name = _('unit')
        verbose_name_plural = _('units')


class PriceType(CatalogDictItemAbstract):
    class Meta:
        verbose_name = _('price type')
        verbose_name_plural = _('price types')


class Stock(models.Model):
    """
    Stock object.
    """

    name = models.CharField(
        _('stock name'), max_length=255, help_text=_('The name of the warehouse.')
    )
    address = models.CharField(
        _('stock address'), max_length=256, help_text=_('Warehouse address.')
    )
    geo_latitude = models.DecimalField(
        _('latitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_('latitude of the stock location'),
    )
    geo_longitude = models.DecimalField(
        _('longitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_('longitude of the stock location'),
    )
    location = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_('Warehouse location.'),
    )
    third_party_code = models.CharField(
        _('third-party system code'), max_length=64, unique=True, null=True, blank=True
    )
    pickup_point = models.BooleanField(_('available as pickup point'), default=True)

    position = models.PositiveSmallIntegerField(_('position'), default=0)

    objects = LocationModelManager()

    class Meta:
        ordering = ('position',)
        verbose_name = _('stock')
        verbose_name_plural = _('stocks')

    def __str__(self):
        return self.name


class ProductStockAvailability(models.Model):
    """
    Product's availability in a certain stock.
    If a product is not available in a stock - there is no record.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='stocks_availability'
    )
    warehouse = models.ForeignKey(Stock, on_delete=models.CASCADE)
    # if available == 0 then the record is deleted/not saved
    available = models.FloatField(default=0)

    def save(self, *args, **kwargs):
        if self.available <= 0:
            # delete this record because the product is not available in this shop
            if self.pk:
                self.delete()
        else:
            super().save(*args, **kwargs)

    class Meta:
        unique_together = (('product', 'warehouse'),)
        verbose_name = _('product availability in stock')
        verbose_name_plural = _('product availability in stocks')

    @property
    def available_value(self):
        try:
            if self.available.is_integer():
                return int(self.available)
        except AttributeError:
            pass

        return self.available


class ProductAvailabilityStatus(models.Model):
    """
    Product availability status in stock.
    It makes it possible to set the name of the status when a stock of a product is in a given range.
    """

    name = models.CharField(_('name'), max_length=256, unique=True)
    range_from = models.PositiveIntegerField(_('range from'))
    range_to = models.PositiveIntegerField(_('range to'))

    def clean(self):
        if self.range_to <= self.range_from:
            raise ValidationError(_('Invalid range specified'))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('product availability status')
        verbose_name_plural = _('product availability statuses')


class ProductPriceHistory(models.Model):
    product = models.ForeignKey(
        Product,
        verbose_name=_('product'),
        related_name='history_prices',
        on_delete=models.CASCADE,
    )
    price = models.DecimalField(
        _('price'),
        max_digits=12,
        decimal_places=2,
        db_index=True,
        null=True,
        blank=True,
    )
    created = models.DateField(
        _('created date'), default=timezone.datetime.today, db_index=True
    )
    location = models.ForeignKey(Location, null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('history price')
        verbose_name_plural = _('history prices')
        # unique_together = (('location', 'product'),)


class ProductSet(models.Model):
    """
    A block with a set of several special products.
    """

    key = models.SlugField(
        _('key'),
        primary_key=True,
        max_length=70,
        help_text=_(
            'The value should only consist of Latin letters, numbers, '
            'underscores or hyphens.'
        ),
    )
    title = models.CharField(_('block title'), max_length=255)
    rows = models.PositiveSmallIntegerField(_('number rows'), default=1)
    banners = models.BooleanField(_('show banners'), default=False)
    # products_per_row = models.PositiveSmallIntegerField(
    #     'кол-во товаров на строку', default=5)

    data_sm_rows = models.PositiveSmallIntegerField('data-sm-rows', default=1)
    data_slides = models.PositiveSmallIntegerField('data-slides', default=1)
    data_sm_slides = models.PositiveSmallIntegerField('data-sm-slides', default=1)
    data_md_slides = models.PositiveSmallIntegerField('data-md-slides', default=2)
    data_lg_slides = models.PositiveSmallIntegerField('data-lg-slides', default=3)
    data_xl_slides = models.PositiveSmallIntegerField('data-xl-slides', default=5)

    class Meta:
        verbose_name = _('product set')
        verbose_name_plural = _('product sets')

    def __str__(self):
        return self.title


class ProductSetMembership(models.Model):
    set = models.ForeignKey(
        ProductSet, on_delete=models.CASCADE, related_name='products'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sets')
    position = models.PositiveSmallIntegerField(_('position'), default=0)
    published = models.BooleanField(_('show'), default=True)

    class Meta:
        verbose_name = _('product in set')
        verbose_name_plural = _('products in set')
        ordering = [
            'position',
        ]


MOYSKLAD_OPERATION_PRICE_UPDATE, MOYSKLAD_OPERATION_STOCK_UPDATE = range(2)
MOYSKLAD_OPERATION_CHOICES = (
    (MOYSKLAD_OPERATION_PRICE_UPDATE, _('price update')),
    (MOYSKLAD_OPERATION_STOCK_UPDATE, _('stock update')),
)


class MoySkladSyncLog(models.Model):
    operation = models.SmallIntegerField(
        _('operation type'), choices=MOYSKLAD_OPERATION_CHOICES
    )
    log = models.TextField(_('log messages'), null=True, blank=True)
    summary = models.TextField(_('sync summary'), null=True, blank=True)
    start_dt = models.DateTimeField(_('start datetime'))
    end_dt = models.DateTimeField(_('end datetime'))

    class Meta:
        verbose_name = _('moy sklad sync log')
        verbose_name_plural = _('moy sklad sync logs')

    def __str__(self):
        return f'{self.operation} {self.start_dt}'


class Currency(models.Model):
    code = LowerCaseCharField(
        _('код валюты'),
        max_length=3,
        unique=True,
        help_text=_(
            'Трехбуквенный код валюты, соответсвующий '
            'ее обозначению в международной системе '
            'стандартов наименования.'
        ),
    )
    symbol = models.CharField(_('символ валюты'), max_length=8)
    is_default = models.BooleanField(_('валюта по-умолчанию'), default=False)
    rate = models.DecimalField(
        _('курс валюты'),
        max_digits=12,
        decimal_places=2,
        help_text=_('Коэффициeнт, на который будут умножаться "не основные" валюты'),
    )

    class Meta:
        verbose_name = _('валюта')
        verbose_name_plural = _('валюты')

    def __str__(self):
        return self.code

    @classmethod
    def get_default(cls):
        return cls.objects.filter(is_default=True).first()


class YmlCustomExport(models.Model):
    CATEGORY = 1
    PRODUCT = 2
    TYPE_CHOICES = ((CATEGORY, _('Категории')), (PRODUCT, _('Товары')))
    URL_FORMAT = f'{settings.YML_EXPORT_CATALOG_URL}{{slug}}.yml'
    type = models.PositiveSmallIntegerField(_('Тип'), choices=TYPE_CHOICES)
    slug = SlugPreviewField(
        _('slug'),
        help_text=_('URL-key'),
        url_format=URL_FORMAT,
        unique=True,
        slugify=slugify,
    )
    categories = models.ManyToManyField(
        Category, verbose_name=_('Категории'), blank=True
    )

    class Meta:
        verbose_name = _('Yml экспорт товаров')
        verbose_name_plural = _('Yml экспорт товаров')

    def __str__(self):
        return self.get_absolute_url()

    def get_absolute_url(self):
        return f'{settings.YML_EXPORT_CATALOG_URL}{self.slug}.yml'

    def get_absolute_url_format(self):
        return f'{settings.YML_EXPORT_CATALOG_URL}{{slug}}.yml'


class YmlCustomProductExport(models.Model):
    export = models.ForeignKey(YmlCustomExport, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.product)

    class Meta:
        verbose_name = _('Экспорт продукта')
        verbose_name_plural = _('Экспорт продуктов')
