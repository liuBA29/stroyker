from rest_framework import viewsets

from stroykerbox.apps.commerce.models import Order
from stroykerbox.apps.drf_tracker.mixins import LoggingMixin

from .serializers import OrderSerializer, OrderUpdateSerializer


class OrderViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    List and update orders.

    retrieve:
    Return the given order.

    list:
    Return a list of all the existing orders.

    partial_update:
    Partial update the given order instance.
    """

    queryset = Order.objects.select_related(
        'user',
        'delivery_type',
        'location',
    )
    # only read and partial_update allowed
    http_method_names = ['get', 'patch']

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return OrderUpdateSerializer
        return OrderSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset
