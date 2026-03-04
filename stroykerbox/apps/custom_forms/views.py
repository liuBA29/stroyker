from django.http import JsonResponse
from django.http.response import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.conf import settings
from django_drf_filepond.api import store_upload

from .models import CustomForm, CustomFormResult
from .forms import CFForm
from .fields import PseudoFileField
from .utils import random_filedir


def form_action(request, key):
    custom_form_obj = get_object_or_404(CustomForm, key=key)
    if request.method == 'POST':
        form = CFForm(custom_form_obj, request.POST, request.FILES)
        if form.is_valid():
            for filefield_name in request.FILES.keys():
                if filefield_name not in form.cleaned_data:
                    continue
                paths_inside_media = []
                for file in form.files.getlist(filefield_name):
                    path_inside_media = f'/uploads/{file.name}'
                    destination = f'{settings.MEDIA_ROOT}{path_inside_media}'
                    paths_inside_media.append(path_inside_media)
                    with open(destination, 'wb+') as file_dest:
                        for chunk in file.chunks():
                            file_dest.write(chunk)
                form.cleaned_data[filefield_name] = paths_inside_media

            for field_name, field_obj in form.fields.items():
                if isinstance(field_obj, PseudoFileField):
                    file_urls = []
                    for upload_id in form.data.getlist(field_name):
                        store_obj = store_upload(
                            upload_id, random_filedir('uploads'))
                        file_urls.append(store_obj.file.url)
                    form.cleaned_data[field_name] = file_urls

            location = getattr(request, 'location', None) or None
            page_url = request.POST.get('form_page_url')

            if page_url:
                page_url = request.build_absolute_uri(page_url)

            CustomFormResult.objects.create(
                form=custom_form_obj,
                results=form.cleaned_data,
                location=location,
                page_url=page_url
            )
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'errors': form.errors})

    return HttpResponseBadRequest()
