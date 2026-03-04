from django.http import HttpResponse
from django.db.models import F

from .models import Banner


def ajax_increase_view_counter(request):
    if request.is_ajax() and request.method == 'POST':
        pk = request.POST.get('pk')
        if pk:
            Banner.objects.filter(pk=pk).update(
                views_counter=F('views_counter') + 1)
    return HttpResponse(status=204)


def ajax_increase_click_counter(request):
    if request.is_ajax() and request.method == 'POST':
        pk = request.POST.get('pk')
        if pk:
            Banner.objects.filter(pk=pk).update(
                clicks_counter=F('clicks_counter') + 1)
    return HttpResponse(status=204)
