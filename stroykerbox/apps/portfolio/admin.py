from django import forms
from django.contrib import admin

from stroykerbox.apps.common.admin import CKEditorModelAdmin
from stroykerbox.apps.custom_forms.utils import custom_form_help_text
from . import models


class PortfolioImageInline(admin.TabularInline):
    model = models.PortfolioImage
    extra = 0


class PortfolioItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].help_text += custom_form_help_text

    class Meta:
        model = models.Portfolio
        exclude = ()


@admin.register(models.Portfolio)
class PortfolioItemAdmin(CKEditorModelAdmin):
    form = PortfolioItemForm
    list_display = ('name', 'category', 'published', 'position')
    list_editable = (
        'published',
        'position',
    )
    ckeditor_fields = ('description',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = (PortfolioImageInline,)


@admin.register(models.PortfolioCategory)
class PortfolioItemTypeAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
