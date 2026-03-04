from rest_framework import serializers

from stroykerbox.apps.crm.models import CrmRequestBase
from stroykerbox.apps.api.commerce.serializers import OrderSerializer
from stroykerbox.apps.users.models import User


class CrmOrderUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ('user_permissions', 'password')


class CrmOrderSerializer(OrderSerializer):
    user = CrmOrderUserSerializer(read_only=True)


class CrmRequestBaseSerializer(serializers.ModelSerializer):
    order = CrmOrderSerializer(read_only=True)

    class Meta:
        model = CrmRequestBase
        fields = '__all__'
