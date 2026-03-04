from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.utils.functional import SimpleLazyObject
from django_geoip.base import storage_class

from .models import Location

GET_PARAM_REGION_NAME = 'region'


def get_location(request):
    from django_geoip.base import Locator
    region_slug = request.GET.get(GET_PARAM_REGION_NAME)
    if region_slug:
        return Location.objects.filter(slug=region_slug).first()
    if not hasattr(request, '_cached_location'):
        request._cached_location = Locator(request).locate()
    return request._cached_location


class LocationMiddleware(MiddlewareMixin):

    def process_request(self, request):
        """ Don't detect location, until we request it implicitly """
        if not request.path.startswith((settings.MEDIA_URL, settings.STATIC_URL, '/admin/')):
            request.location = SimpleLazyObject(lambda: get_location(request))

    def process_response(self, request, response):
        """ Do nothing, if process_request never completed (redirect)"""
        if not hasattr(request, 'location'):
            return response

        storage = storage_class(request=request, response=response)
        try:
            storage.set(location=request.location)
        except ValueError:
            # bad location_id
            pass
        return response
