from django.utils.translation import ugettext as _

from rest_framework import serializers
from rest_framework.utils import model_meta
from uuslug import slugify

from stroykerbox.apps.catalog import models as catalog_models
from stroykerbox.apps.locations.models import Location


class ProductPropsSerializer(serializers.ModelSerializer):
    class Meta:
        model = catalog_models.ProductProps
        fields = ('name', 'slug', 'value', 'position')


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter_value = serializers.StringRelatedField(many=True)

    class Meta:
        model = catalog_models.ProductParameterValueMembership
        fields = ('parameter', 'parameter_value')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.parameter:
            data['parameter'] = instance.parameter.name
        return data


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = catalog_models.ProductImage
        fields = ('image',)


class ProductSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()
    images = ProductImageSerializer(many=True, read_only=True)
    params = ProductParameterSerializer(many=True, read_only=True)
    props = ProductPropsSerializer(many=True, read_only=True)

    class Meta:
        model = catalog_models.Product
        fields = [
            'name',
            'sku',
            'location',
            'categories',
            'published',
            'currency',
            'price',
            'price_from',
            'price_from_to',
            'price_in_compete',
            'purchase_price',
            'old_price',
            'stock',
            'price_type',
            'uom',
            'is_hit',
            'is_new',
            'is_sale',
            'discounted',
            'weight',
            'volume',
            'length',
            'width',
            'height',
            'images',
            'short_description',
            'description',
            'description2',
            'created_at',
            'updated_at',
            'params',
            'props',
            'days_to_arrive',
            'yml_export',
            'modification_code',
            'multiplicity',
            'multiplicity_label',
        ]

    def get_stock(self, obj):
        return obj.available_items_count(location=self.context['location'])

    def get_location(self, obj):
        location = self.context['location']
        if location:
            return location.name
        return _('Default Location')

    def to_internal_value(self, data):
        currency_code = data.get('currency')
        if currency_code:
            try:
                currency = catalog_models.Currency.objects.get(code=currency_code)
                data['currency'] = currency.id
            except catalog_models.Currency.DoesNotExist:
                pass

        return super().to_internal_value(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['categories'] = [c.name for c in instance.categories.all()]
        data['price_type'] = instance.price_type.name if instance.price_type else ''
        data['uom'] = instance.uom.name if instance.uom else ''
        if instance.currency:
            data['currency'] = instance.currency.code

        location = self.context['location']
        if location:
            try:
                price_object = catalog_models.ProductLocationPrice.objects.get(
                    location_id=location.id, product_id=instance.id
                )
            except catalog_models.ProductLocationPrice.DoesNotExist:
                data['price'] = data['old_price'] = data['purchase_price'] = ''
            else:
                data['price'] = price_object.price
                data['old_price'] = price_object.old_price
                data['purchase_price'] = price_object.purchase_price
        return data

    def product_update(self, product, validated_data):
        serializers.raise_errors_on_nested_writes('update', self, validated_data)
        info = model_meta.get_field_info(product)

        # https://redmine.nastroyker.ru/issues/17046
        if validated_data.get('price') in (0, ''):
            validated_data['price'] = None

        # Simply set each attribute on the product, and then save it.
        # Note that unlike `.create()` we don't need to treat many-to-many
        # relationships as being a special case. During updates we already
        # have an product pk for the relationships to be associated with.
        m2m_fields = []
        for attr, value in validated_data.items():

            if attr in info.relations and info.relations[attr].to_many:
                m2m_fields.append((attr, value))
            else:
                setattr(product, attr, value)

        force = bool(validated_data.get('price_in_compete'))

        product.save(force=force)

        # Note that many-to-many fields are set after updating product.
        # Setting m2m fields triggers signals which could potentially change
        # updated product and we do not want it to collide with .update()
        for attr, value in m2m_fields:
            field = getattr(product, attr)
            field.set(value)

        return product

    def update(self, instance, validated_data):
        location = self.context.get('location')
        if location:
            kwargs = {}
            for price_item in ('price', 'old_price', 'purchase_price'):
                if price_item in validated_data:
                    kwargs[price_item] = validated_data.pop(price_item)

            price_object_qs = catalog_models.ProductLocationPrice.objects.filter(
                location_id=location.id, product_id=instance.id
            )
            if price_object_qs.exists():
                price_object_qs.update(**kwargs)
            else:
                kwargs.update({'location': location, 'product': instance})
                catalog_models.ProductLocationPrice.objects.create(**kwargs)

        return self.product_update(instance, validated_data)


class ProductListSerializer(ProductSerializer):

    class Meta:
        model = catalog_models.Product
        fields = [
            'name',
            'sku',
            'location',
            'categories',
            'published',
            'currency',
            'price',
            'price_in_compete',
            'purchase_price',
            'old_price',
            'price_from',
            'price_from_to',
            'stock',
            'price_type',
            'multiplicity',
            'multiplicity_label',
            'uom',
            'is_hit',
            'is_new',
            'is_sale',
            'discounted',
            'weight',
            'volume',
            'length',
            'width',
            'height',
            'images',
            'created_at',
            'updated_at',
            'params',
            'props',
            'yml_export',
            'modification_code',
        ]


class StockSerializer(serializers.ModelSerializer):
    id = serializers.ModelField(
        model_field=catalog_models.Stock()._meta.get_field('id')
    )

    class Meta:
        model = catalog_models.Stock
        fields = '__all__'


class ProductStockAvailabilitySerializer(serializers.ModelSerializer):
    warehouse = StockSerializer()

    class Meta:
        model = catalog_models.ProductStockAvailability
        fields = ('available', 'warehouse')


class ProductStockSerializer(serializers.ModelSerializer):
    stocks_availability = ProductStockAvailabilitySerializer(
        many=True,
        help_text=_(
            'An array containing the store identifier data and the '
            'remainder of this product in it. '
            'Example: [{ "available": 1000, "warehouse": { "id": 1 } } ]'
        ),
    )

    class Meta:
        model = catalog_models.Product
        fields = ('name', 'sku', 'stocks_availability')

    def update(self, instance, validated_data):
        stocks_availability = validated_data.get('stocks_availability')

        if stocks_availability:
            for stock in stocks_availability:
                catalog_models.ProductStockAvailability.objects.update_or_create(
                    product_id=instance.id,
                    warehouse_id=stock['warehouse']['id'],
                    defaults={'available': stock['available']},
                )

        return instance


class LocationPriceSerializer(serializers.ModelSerializer):

    class Meta:
        model = catalog_models.ProductLocationPrice
        fields = ('location', 'price', 'old_price', 'purchase_price')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.location:
            data['location'] = instance.location.name
        return data

    def to_internal_value(self, data):
        try:
            location = Location.objects.get(name__iexact=data['location'])
        except Location.DoesNotExist:
            raise serializers.ValidationError(
                f'Города с названием {data["location"]} не найдено.'
            )
        else:
            data['location'] = location.id

        for i in ('old_price', 'purchase_price'):
            if i not in data:
                data[i] = None
        return super().to_internal_value(data)


class ProductPriceSerializer(serializers.ModelSerializer):
    location_prices = LocationPriceSerializer(many=True)
    currency = serializers.CharField(source='currency.code', required=False)

    class Meta:
        model = catalog_models.Product
        fields = (
            'sku',
            'currency',
            'price',
            'location_prices',
            'multiplicity',
            'multiplicity_label',
        )

    def update(self, instance, validated_data):
        currency_code = validated_data.get('currency')
        currency = None
        if currency_code and isinstance(currency_code, dict):
            currency_code = currency_code.get('code')
        if currency_code:
            try:
                currency = catalog_models.Currency.objects.get(code=currency_code)
            except catalog_models.Currency.DoesNotExist:
                pass

        location_prices = validated_data.get('location_prices')

        if 'price' in validated_data:
            instance.price = validated_data.get('price')

        instance.currency = currency
        instance.save()

        for price in location_prices:

            catalog_models.ProductLocationPrice.objects.update_or_create(
                product_id=instance.id,
                location_id=price['location'].id,
                defaults={
                    'price': price.get('price'),
                    'old_price': price.get('old_price'),
                    'purchase_price': price.get('purchase_price'),
                },
            )

        return instance


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = catalog_models.Category
        exclude = ('rght', 'lft', 'level', 'tree_id')

    def create(self, validated_data):
        """
        Create and return a new `Category` instance, given the validated data.
        """
        if not validated_data.get('slug'):
            validated_data['slug'] = slugify(validated_data['name'])
        return catalog_models.Category.objects.create(**validated_data)


class WarehouseSerializer(serializers.ModelSerializer):

    class Meta:
        model = catalog_models.Stock
        exclude = []


class UomSerializer(serializers.ModelSerializer):

    class Meta:
        model = catalog_models.Uom
        fields = '__all__'


class ProductImageSetSerializer(serializers.ModelSerializer):
    # product_sku = serializers.CharField(
    #     source='product.sku',
    #     read_only=True
    # )
    image = serializers.ImageField()

    class Meta:
        model = catalog_models.ProductImage
        # fields = ('product_sku', 'image', 'position')
        fields = ('image', 'position')


class ProductImageFromUrlSerializer(ProductImageSetSerializer):
    image = serializers.CharField()

    class Meta(ProductImageSetSerializer.Meta):
        pass
