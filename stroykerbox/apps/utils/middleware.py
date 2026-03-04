from django.contrib.redirects.middleware import RedirectFallbackMiddleware
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.redirects.models import Redirect
from django.conf import settings
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.urls import resolve
from django.contrib.auth import REDIRECT_FIELD_NAME as REDIRECT_FIELD_NAME_DEFAULT
from constance import config

REDIRECT_FIELD_NAME = getattr(
    settings, 'LOGIN_REQUIRED_REDIRECT_FIELD_NAME', REDIRECT_FIELD_NAME_DEFAULT)

LOGIN_REQUIRE_EXLUDE_PATHS = ('/account/', '/admin/', '/api')


class CustomRedirectFallbackMiddleware(RedirectFallbackMiddleware):
    def process_response(self, request, response):
        if response.status_code != 404:
            return response

        full_path = request.get_full_path()
        current_site = get_current_site(request)

        r = None
        try:
            r = Redirect.objects.get(
                site=current_site, old_path__iexact=full_path)
        except Redirect.DoesNotExist:
            pass
        except Redirect.MultipleObjectsReturned:
            r = Redirect.objects.filter(
                site=current_site, old_path__iexact=full_path).first()

        if r is None and settings.APPEND_SLASH and not request.path.endswith("/"):
            try:
                r = Redirect.objects.get(
                    site=current_site,
                    old_path__iexact=request.get_full_path(
                        force_append_slash=True),
                )
            except Redirect.DoesNotExist:
                pass
            except Redirect.MultipleObjectsReturned:
                r = Redirect.objects.filter(
                    site=current_site,
                    old_path__iexact=request.get_full_path(
                        force_append_slash=True),
                ).first()

        if r is not None:
            if r.new_path == "":
                return self.response_gone_class()
            return self.response_redirect_class(r.new_path)

        # No redirect was found. Return the response.
        return response


class LoginRequiredMiddleware(AuthenticationMiddleware):
    @staticmethod
    def _login_required(request):
        if not config.GLOBAL_ACCESS_AUTHORIZED_ONLY or any(
                (
                    request.user.is_authenticated,
                    request.path.startswith(LOGIN_REQUIRE_EXLUDE_PATHS)
                )
        ):
            return None

        try:
            resolver = resolve(request.path)
        except Http404:
            return redirect_to_login(request.get_full_path())

        view_func = resolver.func

        if not getattr(view_func, 'login_required', True):
            return None

        view_class = getattr(view_func, 'view_class', None)
        if view_class and not getattr(view_class, 'login_required', True):
            return None

        return redirect_to_login(request.get_full_path(), redirect_field_name=REDIRECT_FIELD_NAME)

    def process_request(self, request):
        return self._login_required(request)
