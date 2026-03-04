from django.conf import settings
from rest_framework import permissions


class AllowedIP(permissions.BasePermission):
    """
    Global permission check for allowed IPs.
    """

    def has_permission(self, request, view):
        ip_addr = request.META.get('REMOTE_ADDR', None)
        try:
            has_perm = ip_addr in getattr(settings, 'REST_FRAMEWORK_ALLOWED_IPS', [])
        except Exception:
            return False
        return has_perm or bool(request.user and request.user.is_staff)


class AllowedKey(permissions.BasePermission):
    """
    Global permission check for allowed IPs.
    """

    def has_permission(self, request, view):
        key = request.META.get('HTTP_X_STROYKER_KEY', None)
        try:
            has_perm = key in getattr(settings, 'REST_FRAMEWORK_ALLOWED_KEYS', [])
        except Exception:
            return False
        return has_perm or bool(request.user and request.user.is_staff)
