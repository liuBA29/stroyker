from django import forms
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.urls import path, reverse
from django.core.management import call_command
from django.http import HttpResponseRedirect

from mptt.admin import MPTTModelAdmin
from import_export.admin import ImportExportMixin
from ckeditor.widgets import CKEditorWidget

from stroykerbox.apps.custom_forms.utils import custom_form_help_text

from .models import (
    File,
    Page,
    PageImage,
    PageCustomCss,
    PageCustomFiles,
    PageCustomJs,
    PageContructor,
    PageContructorBlock,
    PageParendBreadcrumb,
)


class FileInline(admin.TabularInline):
    model = File
    extra = 0


class PageCustomFileInlineMixin:
    extra = 0
    exclude = ('file_type',)
    sortable_field_name = 'position'


class PageCustomCssInline(PageCustomFileInlineMixin, admin.TabularInline):
    model = PageCustomCss

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(file_type='css')


class PageCustomJsInline(PageCustomFileInlineMixin, admin.TabularInline):
    model = PageCustomJs

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.filter(file_type='js')


class PageImageInline(admin.TabularInline):
    model = PageImage
    extra = 0
    sortable_field_name = 'position'


class PageForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].help_text += custom_form_help_text

    class Meta:
        model = Page
        exclude = ()


@admin.register(Page)
class PageAdmin(ImportExportMixin, MPTTModelAdmin):
    form = PageForm
    list_display = ('title', 'key', 'published', 'position', 'use_editor')
    list_editable = ('use_editor',)
    list_filter = ('published',)
    inlines = [PageImageInline, FileInline, PageCustomCssInline, PageCustomJsInline]
    fieldsets = (
        (
            '',
            {
                'fields': (
                    'title',
                    'parent',
                    'container',
                    'related_productset',
                    'url',
                    'key',
                    'teaser_image',
                    'text',
                    'position',
                    'wide_view',
                    'no_wrapper',
                    'published',
                    'use_editor',
                ),
            },
        ),
        (
            _('Meta'),
            {
                'classes': ('collapse',),
                'fields': ('meta_keywords', 'meta_description'),
            },
        ),
    )
    sortable_field_name = 'position'
    change_list_filter_template = 'admin/filter_listing.html'
    change_list_template = "staticpages/admin/staticpages_changelist.html"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not obj or obj.use_editor:
            # https://redmine.nastroyker.ru/issues/19241
            form.base_fields['text'].widget = CKEditorWidget()
        return form

    def get_readonly_fields(self, request, obj=None):
        if hasattr(obj, 'key'):
            return ('key',)
        else:
            return super().get_readonly_fields(request, obj)

    def get_urls(self):
        urls = super().get_urls()
        return [
            path(
                'update_pages_search_index/',
                self.update_search_index,
                name='update_pages_search_index',
            ),
        ] + urls

    def update_search_index(self, request):
        call_command('update_search_index', '--staticpages', verbosity=0)
        self.message_user(
            request, _('The search index for a pages was successfully updated.')
        )
        return HttpResponseRedirect(reverse('admin:staticpages_page_changelist'))


class PageContructorBlockInline(admin.TabularInline):
    model = PageContructorBlock
    extra = 0


class PageParendBreadcrumbInline(admin.TabularInline):
    model = PageParendBreadcrumb
    extra = 0


class PageCustomFilesInline(admin.TabularInline):
    model = PageCustomFiles
    extra = 0


@admin.register(PageContructor)
class PageContructorAdmin(admin.ModelAdmin):
    inlines = (
        PageParendBreadcrumbInline,
        PageContructorBlockInline,
        PageCustomFilesInline,
    )
    list_display = ('title', 'key')

    def get_prepopulated_fields(self, request, obj=None):
        if not hasattr(obj, 'key'):
            return {'key': ('title',)}
        return super().get_prepopulated_fields(request, obj)
