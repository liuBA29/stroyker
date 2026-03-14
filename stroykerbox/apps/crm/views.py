from typing import Optional
from logging import getLogger

from django.http import JsonResponse
from django.http.response import HttpResponseBadRequest
from django.views.generic import View
from django.shortcuts import redirect
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.forms import Form

from .forms import FeedbackMessageForm, CallMeForm, GiftForPhoneRequestForm


logger = getLogger(__name__)


def _request_wants_json(request):
    """Проверка AJAX/JSON-запроса (совместимо с Django 4+, где убран is_ajax())."""
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


class CrmFormViewBase(View):
    form_class: Optional[Form] = None

    def post(self, request, **kwargs):
        success = False
        if self.form_class:
            form = self.form_class(request.POST)
            errors = form.errors if form.errors else None
            if errors:
                logger.error(errors)
            if form.is_valid():
                success = True
                result = form.save(commit=False)
                result.location = request.location or None
                try:
                    result.save()
                except Exception as e:
                    logger.error(e)
            if _request_wants_json(request):
                # Сериализуем errors в обычный dict для JSON (Django ErrorDict не всегда напрямую сериализуется)
                errors_serializable = None
                if errors:
                    errors_serializable = {k: list(v) for k, v in errors.items()}
                payload = {'success': success, 'errors': errors_serializable}
                if success:
                    payload['msg'] = _('Ваше сообщение отправлено!')
                return JsonResponse(payload)
        return redirect(request.POST.get('page_url') or '/')


class FeedbackMessageView(CrmFormViewBase):
    form_class = FeedbackMessageForm


class CallMeRequestView(CrmFormViewBase):
    form_class = CallMeForm


class GiftForPhoneRequestView(View):
    form_class = GiftForPhoneRequestForm

    def post(self, request, **kwargs):
        if not _request_wants_json(request):
            return HttpResponseBadRequest()

        form = self.form_class(request.POST)
        response = {
            'success': False,
            'errors': None,
            'msg': None,
        }

        if form.errors:
            logger.error(form.errors)

        if form.is_valid():
            response['success'] = True
            result = form.save(commit=False)
            location = getattr(request, 'location', None)
            if location:
                result.location = location
            if request.user.is_authenticated:
                name = request.user.email
            else:
                name = _('Anonymous')
            result.name = name
            result.save()
            response['msg'] = render_to_string(
                'crm/include/gift-for-phone-response.html')
        else:
            response['errors'] = form.errors
        return JsonResponse(response)
