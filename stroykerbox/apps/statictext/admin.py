from django.contrib import admin
from django import forms

from ckeditor.widgets import CKEditorWidget

from .models import Statictext


class StatictextAdminForm(forms.ModelForm):
    text = forms.CharField(widget=CKEditorWidget())

    class Meta:
        model = Statictext
        exclude = ('key',)


@admin.register(Statictext)
class StatictextAdmin(admin.ModelAdmin):
    list_display = ('key', 'comment', 'use_custom_form')
    search_fields = ('key',)

    def get_form(self, request, obj=None, **kwargs):
        if obj and obj.use_editor:
            return StatictextAdminForm
        return super().get_form(request, obj, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and hasattr(obj, 'key'):
            return ('key',)
        return super().get_readonly_fields(request, obj=None)
