from rest_framework.viewsets import ModelViewSet

from stroykerbox.apps.crm.models import CrmRequestBase
from stroykerbox.apps.drf_tracker.mixins import LoggingMixin

from .serializers import CrmRequestBaseSerializer


class CrmRequestBaseViewSet(LoggingMixin, ModelViewSet):
    serializer_class = CrmRequestBaseSerializer
    queryset = CrmRequestBase.objects.select_related(
        'manager',
        'location',
    )
