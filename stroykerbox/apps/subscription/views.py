from django.views.generic import View
from django.http import JsonResponse
from django.http.response import HttpResponseBadRequest

from .forms import SubscriptionForm


class SubscriptionNewView(View):

    def post(self, request, **kwargs):
        success = False
        form = SubscriptionForm(request.POST or None)
        if form.is_valid():
            success = True
            form.save()
        if request.is_ajax():
            errors = form.errors if form.errors else None
            return JsonResponse({'success': success, 'errors': errors})
        return HttpResponseBadRequest()

    def get(self, request, **kwargs):
        return HttpResponseBadRequest()
