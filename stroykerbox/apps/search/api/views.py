from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from stroykerbox.apps.api.permissions import AllowedKey, AllowedIP

from .serializers import SearchQueryDataSerializer
from ..models import SearchQueryData


class SearchQueryView(APIView):
    permission_classes = [IsAdminUser | AllowedKey | AllowedIP]

    def get(self, request):
        """
        Список объектов данных поисковых запросов.
        """
        qs = SearchQueryData.objects.all()

        serializer = SearchQueryDataSerializer(qs, many=True)

        return Response(serializer.data)
