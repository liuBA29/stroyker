from django.contrib import admin, messages
from django import forms
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render

from import_export.admin import ExportMixin
from import_export.formats import base_formats
from ckeditor.widgets import CKEditorWidget
from constance import config

from .models import Partner, PartnerCategory, Contact, PartnerCoordinates, PartnerCity
from .resources import PartnerResourceBase, partner_import_data


class PartnerImportForm(forms.Form):
    file = forms.FileField(label='Файл с данными для импорта')


class AddressBaseAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('position',)


class AddressAdmin(AddressBaseAdmin):
    def city(self, obj):
        return obj.location.city


class PartnerCoordinatesInline(admin.TabularInline):
    model = PartnerCoordinates
    extra = 0


@admin.register(Partner)
class PartnerAdmin(ExportMixin, AddressAdmin):
    list_display = ('name', 'position', 'is_active')
    inlines = (PartnerCoordinatesInline,)
    resource_class = PartnerResourceBase
    change_list_template = 'addresses/admin/partners_changelist.html'
    autocomplete_fields = ('location', 'city')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        # https://redmine.nastroyker.ru/issues/19442
        if config.ADDRESSES_PARTNER_USE_EDITOR:
            form.base_fields['description'].widget = CKEditorWidget()

        return form

    def get_export_formats(self):
        """
        Returns available export formats.
        """
        formats = (base_formats.XLSX,)
        return [f for f in formats if f().can_export()]

    def get_urls(self):
        urls = super().get_urls()
        return [
            path('partner_import/', self.partner_import, name='partner_import'),
        ] + urls

    def partner_import(self, request):
        if request.method == 'POST':
            form = PartnerImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['file']
                try:
                    result_dict = partner_import_data(file)
                    if result_dict:
                        for level_str in result_dict.keys():
                            for msg in result_dict[level_str]:
                                self.message_user(
                                    request, msg, getattr(messages, level_str, 'INFO')
                                )
                except Exception as e:
                    err = f'Ошибка импорта: {e}'
                    self.message_user(request, err, 'ERROR')
                return HttpResponseRedirect(
                    reverse('admin:addresses_partner_changelist')
                )
        form = PartnerImportForm()
        context = {'form': form}
        return render(request, 'addresses/admin/partner_import.html', context)


@admin.register(PartnerCategory)
class PartnerCategoryAdmin(AddressBaseAdmin):
    list_display = ('name', 'id', 'position')


@admin.register(PartnerCity)
class PartnerCityAdmin(AddressBaseAdmin):
    list_display = ('name', 'id', 'position')
    search_fields = ('name',)


class ContactAdminForm(forms.ModelForm):
    extra = forms.CharField(widget=CKEditorWidget())

    class Meta:
        model = Contact
        exclude = []


@admin.register(Contact)
class ContactAdmin(AddressAdmin):
    list_display = ('name', 'city', 'is_active', 'created_at', 'updated_at', 'position')
    form = ContactAdminForm
