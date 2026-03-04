from rest_framework import serializers

from stroykerbox.apps.banners.models import Banner
from stroykerbox.apps.catalog.models import Product
from stroykerbox.apps.api.catalog.serializers import ProductParameterSerializer, ProductPropsSerializer


class OrderStatsSerializer(serializers.Serializer):
    date = serializers.DateField()
    total = serializers.IntegerField()


class CartAmountStatsSerializer(serializers.Serializer):
    date = serializers.DateField()
    amount_rub = serializers.DecimalField(max_digits=12, decimal_places=2)


class CartTopProductsStatsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    name = serializers.CharField(source='product__name')
    sku = serializers.CharField(source='product__sku')


class BannerDisplayUrlField(serializers.RelatedField):
    def to_representation(self, value):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(value.url)
        return value.url


class BannerSerializer(serializers.ModelSerializer):
    img_url = serializers.SerializerMethodField()
    display_urls = BannerDisplayUrlField(many=True, read_only=True)

    class Meta:
        model = Banner
        fields = ('img_url', 'clicks_counter', 'views_counter', 'display_urls')

    def get_img_url(self, banner):
        request = self.context.get('request')
        return request.build_absolute_uri(banner.image_file.url)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.all_pages:
            data['display_urls'] = 'all'
        return data


class CrmRequestSerializer(serializers.Serializer):
    date = serializers.DateField()
    total = serializers.IntegerField()
    total_processed = serializers.IntegerField()
    object_class = serializers.CharField()


class ProductInfoSerializer(serializers.ModelSerializer):
    params = ProductParameterSerializer(many=True, read_only=True)
    props = ProductPropsSerializer(many=True, read_only=True)
    online_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['name', 'sku', 'categories', 'published', 'price', 'online_price',
                  'purchase_price', 'old_price', 'price_type', 'multiplicity', 'multiplicity_label',
                  'uom', 'weight', 'volume', 'length', 'width', 'height', 'description',
                  'created_at', 'updated_at', 'params', 'props']

    def get_online_price(self, product):
        return product.online_price()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['categories'] = [c.name for c in instance.categories.all()]
        data['price_type'] = instance.price_type.name if instance.price_type else ''
        data['uom'] = instance.uom.name if instance.uom else ''

        return data


class CustomFormSerializer(serializers.Serializer):
    form_name = serializers.CharField()
    form = serializers.CharField()
    date = serializers.DateField()
    total = serializers.IntegerField()
