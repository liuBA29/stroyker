from django.utils.translation import ugettext as _
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action

from stroykerbox.apps.users.models import User
from stroykerbox.apps.drf_tracker.mixins import LoggingMixin

from .serializers import UserSerializer, UserDocumentSerializer


class UserViewSet(LoggingMixin, viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    lookup_field = 'email'
    lookup_value_regex = '[^/]+'

    @action(
        methods=['post'],
        detail=True,
        name=_('Add a document for the user'),
        url_path='add-userdoc',
        url_name='add-userdoc',
    )
    def add_userdoc(self, request, pk):
        data = request.data
        data['user'] = pk
        serializer = UserDocumentSerializer(context={'request': request}, data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors)

    def get_serializer_class(self):
        if self.action == 'add_userdoc':
            return UserDocumentSerializer
        return super().get_serializer_class()
