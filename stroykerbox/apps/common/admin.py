from typing import Iterable

from django.contrib import admin

from ckeditor.widgets import CKEditorWidget


class CKEditorModelAdmin(admin.ModelAdmin):

    ckeditor_fields: Iterable = []

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for field in self.ckeditor_fields:
            if field in form.base_fields:
                form.base_fields[field].widget = CKEditorWidget()
        return form
