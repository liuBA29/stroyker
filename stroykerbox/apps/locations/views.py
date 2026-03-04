from django.http import HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings

from django_geoip.base import storage_class
from django_geoip.utils import get_class


def set_location(request, location_id):
    """
    Redirect to a given url while setting the chosen location in the
    cookie. The url and the location_id need to be
    specified in the request parameters.
    """
    next = request.GET.get('next', None) or request.META.get(
        'HTTP_REFERER', None) or '/'

    next = next.split('?')[0]

    response = HttpResponseRedirect(next)

    if location_id:
        try:
            location = get_class(
                settings.GEOIP_LOCATION_MODEL).objects.get(pk=location_id)
            storage_class(request=request, response=response).set(
                location=location, force=True)
        except (ValueError, ObjectDoesNotExist):
            pass

    return response
