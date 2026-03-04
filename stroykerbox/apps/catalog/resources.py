from logging import getLogger
from random import randint

from django.utils.translation import ugettext as _
from django.conf import settings
from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget

from uuslug import uuslug
from constance import config

from stroykerbox.apps.locations.models import Location
from stroykerbox.apps.floatprice.models import FloatPrice

from . import models


logger = getLogger('django')


FLOATPRICE_PERCENT_COLUMN_NAME = 'floatprice_percent'


class CatalogProductExportResource(resources.ModelResource):
    """
    Downloading the list of products of a specific catalog. Only export.
    """

    sku = Field(attribute='sku', column_name=_('Sku'))
    name = Field(attribute='name', column_name=_('Name'))
    price = Field(attribute='price', column_name=_('Price'))
    modification_code = Field(
        attribute='modification_code', column_name=_('Modification Code')
    )
    available_items = Field(column_name=_('Available Count'))
    personal_price = Field(column_name=_('Personal Price'))

    class Meta:
        model = models.Product
        import_id_fields = ('sku',)
        fields = (
            'sku',
            'name',
            'available_items',
            'price',
            'personal_price',
            'modification_code',
            'multiplicity',
            'multiplicity_label',
        )
        export_order = (
            'sku',
            'name',
            'available_items',
            'price',
            'personal_price',
            'modification_code',
            'multiplicity',
            'multiplicity_label',
        )

    def dehydrate_available_items(self, product):
        return product.available_items_count(self.request.location)

    def dehydrate_personal_price(self, product):
        return product.personal_price(self.request.user, self.request.location)

    def export(self, queryset=None, *args, **kwargs):
        self.request = kwargs.get('request', None)
        category = kwargs.get('category', None)
        queryset = category.products.published()
        return super().export(queryset, *args, **kwargs)


class ProductResource(resources.ModelResource):
    """
    Import/export of default location prices and other data for a products.
    """

    categories = Field(
        column_name='categories',
        attribute='categories',
        widget=ManyToManyWidget(models.Category),
    )

    class Meta:
        model = models.Product
        skip_unchanged = True
        import_id_fields = ('sku',)
        fields = (
            'sku',
            'categories',
            'name',
            'price',
            'old_price',
            'multiplicity',
            'multiplicity_label',
            'purchase_price',
            'yml_export',
            'modification_code',
        )
        export_order = fields

    def before_save_instance(self, instance, using_transactions, dry_run):
        if not instance.slug:
            instance.slug = uuslug(instance.name, instance=instance)


class ProductLocationPriceResource(resources.ModelResource):
    """
    Import/export of not-default location prices.
    """

    location = Field(
        column_name='location_city',
        attribute='location',
        widget=ForeignKeyWidget(Location, 'city__name'),
    )

    product = Field(
        column_name='product_sku',
        attribute='product',
        widget=ForeignKeyWidget(models.Product, 'sku'),
    )

    class Meta:
        model = models.ProductLocationPrice
        skip_unchanged = True
        import_id_fields = (
            'location',
            'product',
        )
        fields = ('location', 'product', 'price', 'old_price', 'purchase_price')
        export_order = ('location', 'product', 'price', 'old_price', 'purchase_price')


class ProductStockAvailabilityResource(resources.ModelResource):
    """
    Import/export of stock balances.
    """

    product = Field(
        column_name='product_sku',
        attribute='product',
        widget=ForeignKeyWidget(models.Product, 'sku'),
    )
    product_name = Field(column_name='product_name', attribute='product__name')

    warehouse = Field(
        column_name='stock_name',
        attribute='warehouse',
        widget=ForeignKeyWidget(models.Stock, 'name'),
    )

    class Meta:
        model = models.ProductStockAvailability
        skip_unchanged = True
        import_id_fields = (
            'product',
            'warehouse',
        )
        fields = ('product', 'warehouse', 'available', 'product_name')
        export_order = ('product', 'warehouse', 'available')

    def import_field(self, field, obj, data, is_m2m=False, **kwargs):
        product_name = data.get('product_name')
        if product_name and product_name != obj.product.name:
            obj.product.name = product_name
            obj.product.save(update_fields=('name',))
        return super().import_field(field, obj, data, is_m2m, **kwargs)


class CategoryImportResource(resources.ModelResource):
    parent = Field(
        column_name='parent',
        attribute='parent',
        widget=ForeignKeyWidget(models.Category, 'id'),
    )

    class Meta:
        model = models.Category
        fields = (
            'id',
            'name',
            'slug',
            'image',
            'icon',
            'published',
            'vk_group_id',
            'parent',
        )


class CategoryExportResource(resources.ModelResource):
    url = Field(column_name='url', readonly=True, widget=None)

    parent = Field(
        column_name='parent',
        attribute='parent',
        widget=ForeignKeyWidget(models.Category, 'id'),
    )

    class Meta:
        model = models.Category
        fields = ('id', 'name', 'parent', 'url', 'vk_group_id')
        export_order = fields

    def dehydrate_url(self, category):
        return f'{settings.BASE_URL}{category.get_absolute_url()}'


class ParameterImportResource(resources.ModelResource):
    class Meta:
        model = models.Parameter


class ParameterValueImportResource(resources.ModelResource):
    class Meta:
        model = models.ParameterValue


class CategoryParameterMembershipImportResource(resources.ModelResource):
    category = Field(attribute='category_id')

    class Meta:
        model = models.CategoryParameterMembership


class ProductParameterValueMembershipImportResource(resources.ModelResource):
    id = Field(attribute='id', column_name=_('Product ID'))
    product_name = Field(
        column_name=_('Product Name'),
        attribute='product',
        widget=ForeignKeyWidget(models.Product, 'name'),
    )

    parameter = Field(attribute='id', column_name=_('Parameter ID'))
    parameter_name = Field(
        column_name=_('Parameter Name'),
        attribute='parameter',
        widget=ForeignKeyWidget(models.Parameter, 'name'),
    )

    # parameter_value = Field(attribute='parameter_value_id', column_name=_('Parameter Value IDs'))
    parameter_value = Field(
        column_name=_('Parameter Value IDs'),
        attribute='parameter_value',
        widget=ManyToManyWidget(models.ParameterValue, field='id'),
    )
    parameter_value_name = Field(
        column_name=_('Parameter Value Names'),
        attribute='parameter_value',
        widget=ManyToManyWidget(models.ParameterValue, field='value_str'),
    )

    class Meta:
        model = models.ProductParameterValueMembership


class UomImportResource(resources.ModelResource):
    class Meta:
        model = models.Uom


class ProductResourceBase(resources.ModelResource):
    categories = Field(
        column_name='categories_ids',
        attribute='categories',
        widget=ManyToManyWidget(models.Category),
    )
    currency = Field(
        column_name='currency',
        attribute='currency',
        widget=ForeignKeyWidget(models.Currency, 'code'),
    )

    floatprice_percent = Field(
        attribute='floatprice__percent', column_name=FLOATPRICE_PERCENT_COLUMN_NAME
    )

    class Meta:
        model = models.Product
        import_id_fields = ('sku',)
        fields = (
            'id',
            'sku',
            'name',
            'slug',
            'categories_by_name',
            'categories',
            'description',
            'description2',
            'short_description',
            'currency',
            'price',
            'price_type',
            'purchase_price',
            'old_price',
            'price_from',
            'price_from_to',
            'is_hit',
            'is_new',
            'is_sale',
            'is_action',
            'discounted',
            'uom',
            'weight',
            'volume',
            'length',
            'width',
            'multiplicity',
            'multiplicity_label',
            'height',
            'published',
            'position',
            'days_to_arrive',
            'yml_export',
            'images',
            'modification_code',
            'is_mod_priority',
            'search_words',
            FLOATPRICE_PERCENT_COLUMN_NAME,
        )


class ProductImportResource(ProductResourceBase):

    class Meta(ProductResourceBase.Meta):
        skip_unchanged = config.IMPORT__SKIP_UNCHANGED
        skip_diff = config.IMPORT__SKIP_DIFF
        report_skipped = config.IMPORT__REPORT_SKIPPED

    def skip_row(self, instance, original, row, import_validation_errors=None):
        if config.IMPORT__CREATE_IF_NOT_EXISTS:
            return False
        elif not instance.id:
            return True
        return super().skip_row(instance, original, row, import_validation_errors)

    def import_field(self, field, obj, data, is_m2m=False, **kwargs):
        if getattr(field, 'column_name', None) != FLOATPRICE_PERCENT_COLUMN_NAME:
            return super().import_field(field, obj, data, is_m2m, **kwargs)

        percent = data.get(field.column_name)
        if percent:
            percent = int(percent)
            float_sum = (obj.price / 100) * percent
            float_price = randint(
                int(obj.price - float_sum), int(obj.price + float_sum)
            )
            fp_obj, __ = FloatPrice.objects.update_or_create(
                product=obj, defaults={'price': float_price, 'percent': percent}
            )
            return fp_obj.percent

    def get_or_init_instance(self, instance_loader, row):
        sku = row.get('sku')
        if sku and isinstance(sku, (float, int)):
            row['sku'] = str(int(sku))
        return super().get_or_init_instance(instance_loader, row)

    def before_import_row(self, row, row_number=None, **kwargs):
        return super().before_import_row(row, row_number, **kwargs)


class ProductExportResource(ProductResourceBase):
    categories_by_name = Field(column_name='categories')
    images = Field(column_name='images')

    class Meta:
        model = models.Product
        fields = (
            'id',
            'sku',
            'name',
            'slug',
            'categories_by_name',
            'categories',
            'description',
            'description2',
            'short_description',
            'currency',
            'price',
            'price_type',
            'purchase_price',
            'old_price',
            'price_from',
            'price_from_to',
            'is_hit',
            'is_new',
            'is_sale',
            'is_action',
            'discounted',
            'uom',
            'weight',
            'volume',
            'length',
            'width',
            'multiplicity',
            'multiplicity_label',
            'height',
            'published',
            'position',
            'days_to_arrive',
            'yml_export',
            'images',
            'modification_code',
            'is_mod_priority',
            'search_words',
            FLOATPRICE_PERCENT_COLUMN_NAME,
        )
        export_order = fields

    def dehydrate_images(self, product):
        images = ''
        for img in product.images.all():
            try:
                images += f', {img.image.url}'
            except Exception as e:
                logger.exception(e)
                continue
        return images

    def dehydrate_categories_by_name(self, product):
        return ', '.join([c.name for c in product.categories.all()])


class ProductRelatedResource(resources.ModelResource):
    class Meta:
        model = models.ProductRelated
        skip_unchanged = True
        import_id_fields = (
            'ref__sku',
            'product__sku',
        )
        export_order = fields = (
            'ref__sku',
            'product__sku',
            'position',
        )
