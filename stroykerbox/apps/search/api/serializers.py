from rest_framework import serializers

from ..models import SearchQueryData


class SearchQueryDataSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.email', required=False)

    class Meta:
        model = SearchQueryData
        exclude = []
