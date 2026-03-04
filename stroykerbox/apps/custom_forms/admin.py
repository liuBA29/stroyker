from urllib.parse import quote

from django.conf import settings
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from django.db.models import Model as DjangoModel

from stroykerbox.apps.custom_forms import models
from .fields import PseudoFileField


class CustomSelectFieldChoiceInline(admin.TabularInline):
    model = models.CustomSelectFieldChoiceModel


@admin.register(models.CustomSelectFieldModel)
class CustomSelectFieldAdmin(admin.ModelAdmin):
    inlines = (CustomSelectFieldChoiceInline,)


class CustomFormFieldInline(admin.TabularInline):
    prepopulated_fields = {'html_name': ('label',)}
    model = models.CustomFormField
    extra = 0


@admin.register(models.CustomForm)
class CustomFormAdmin(admin.ModelAdmin):
    list_display = ('title', 'key', 'active')
    list_editable = ('active',)
    inlines = (CustomFormFieldInline,)
    prepopulated_fields = {'key': ('title',)}


def make_link(file_url: str) -> str:
    file_name = file_url.split('/')[-1]
    file_ext = file_name.split('.')[-1].lower()
    img_extensions = ('png', 'gif', 'jpeg', 'jpg', 'svg')
    if file_ext in img_extensions:
        return f'<a href="{file_url}" target="_blank"><img style="max-width: 100px" src="{file_url}"/></a>'
    return f'<a href="{file_url}" download>{file_name}</a>'


def prepare_custom_field_data(field_class: str, value: str | list) -> str:
    result = []
    if field_class.endswith(PseudoFileField.__name__):
        for file_url in value:
            result.append(make_link(file_url))
    elif field_class.endswith('FileField'):
        if not isinstance(value, list):
            value = [quote(value)]
        for filepath in value:
            file_url = f'{settings.MEDIA_URL}{quote(filepath)}'.replace('//', '/')
            result.append(make_link(file_url))
    return mark_safe('<br><br><hr><br>'.join(result) if result else value)


def make_dynamic_field(field_name: str, field_class: str) -> str:
    def dynamic_field(obj: DjangoModel) -> str:
        output = ''
        result = obj.results.get(field_name)
        if result:
            output = prepare_custom_field_data(field_class, result)
        return output

    return dynamic_field  # type: ignore


@admin.register(models.CustomFormResult)
class CustomFormResultAdmin(admin.ModelAdmin):
    list_display = ('form_title', 'created')
    list_filter = ('form__title',)
    exclude = ('results', 'page_url')

    def form_title(self, obj):
        return obj.form.title

    def get_object(self, request, object_id, from_field=None):
        object = super().get_object(request, object_id, from_field)
        for f, label, field_class in self.get_custom_fields(object):
            field_name = f.replace('-', '_')
            setattr(self, field_name, make_dynamic_field(f, field_class))
            setattr(getattr(self, field_name, None), 'short_description', label)
        return object

    def get_custom_fields(self, obj=None):
        if obj:
            return obj.form.fields.values_list('html_name', 'label', 'field_class')
        return ()

    def get_readonly_fields(self, request, obj=None):
        if not obj:
            fields = super().get_readonly_fields(request, obj)
        else:
            fields = [f.replace('-', '_') for f, __, ___ in self.get_custom_fields(obj)]
        fields.append('page_url_as_link')
        return fields

    def page_url_as_link(self, obj):
        if obj.page_url:
            return format_html(
                f'<a target="_blank" href="{obj.page_url}">{obj.page_url}</a>'
            )
        return ''

    page_url_as_link.short_description = _('URL страницы отправки')  # type: ignore
    page_url_as_link.allow_tags = True  # type: ignore
