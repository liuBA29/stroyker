from django.utils.translation import ugettext as _

from rest_framework import serializers
from stroykerbox.apps.commerce.models import Order, OrderProductMembership


class OrderProductSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    sku = serializers.SerializerMethodField()

    class Meta:
        model = OrderProductMembership
        fields = ['name', 'sku', 'quantity', 'product_price',
                  'personal_product_price']

    def get_name(self, obj):
        return obj.product.name

    def get_sku(self, obj):
        return obj.product.sku


class OrderSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    delivery = serializers.SerializerMethodField()
    order_contact_person = serializers.SerializerMethodField()
    order_email = serializers.SerializerMethodField()
    order_phone = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    payment_method = serializers.SerializerMethodField()
    order_products = OrderProductSerializer(many=True, read_only=True)
    pickup_point = serializers.SerializerMethodField()
    pickup_point_id = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'total_price', 'final_price', 'is_paid', 'status',
                  'status_changed_at', 'comment', 'created_at', 'payment_method',
                  'invoicing_with_vat', 'from_cart', 'user', 'delivery', 'location',
                  'order_products', 'order_contact_person', 'order_email',
                  'order_phone', 'pickup_point', 'pickup_point_id')

    def get_order_contact_person(self, obj):
        if hasattr(obj.delivery, 'name'):
            return obj.delivery.name
        return ''

    def get_order_email(self, obj):
        if hasattr(obj.delivery, 'email'):
            return obj.delivery.email
        return ''

    def get_order_phone(self, obj):
        if hasattr(obj.delivery, 'phone'):
            return obj.delivery.phone
        return ''

    def get_location(self, obj):
        if obj.location:
            return obj.location.name
        return _('Default Location')

    def get_delivery(self, obj):
        return obj.delivery.__str__()

    def get_payment_method(self, obj):
        return obj.payment_method_name

    def get_user(self, obj):
        if obj.user:
            return obj.user.email
        return _('Anonymous')

    def get_pickup_point(self, obj):
        if hasattr(obj.delivery, 'point'):
            return getattr(obj.delivery.point, 'address', None)

    def get_pickup_point_id(self, obj):
        if hasattr(obj.delivery, 'point'):
            return getattr(obj.delivery.point, 'id', None)


class OrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ('is_paid', 'shipped', 'status', 'comment')
