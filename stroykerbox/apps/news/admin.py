from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from sorl.thumbnail import get_thumbnail
from sorl.thumbnail.admin import AdminImageMixin
from django.utils.html import mark_safe
from ckeditor.widgets import CKEditorWidget

from .models import News, NewsImage, NewsFile


class NewsImageInline(admin.TabularInline):
    model = NewsImage
    extra = 0
    sortable_field_name = 'position'


class NewsFileInline(admin.TabularInline):
    model = NewsFile
    extra = 0
    sortable_field_name = 'position'


class NewsAdmin(AdminImageMixin, admin.ModelAdmin):

    inlines = [NewsFileInline, NewsImageInline]
    list_display = ('post_type', 'date', 'preview', 'title', 'published', 'use_editor')
    list_editable = ('published', 'use_editor')
    list_display_links = ('date', 'preview', 'title')
    list_filter = ('date', 'post_type')
    prepopulated_fields = {'slug': ('title',)}

    def preview(self, obj):
        if obj.image:
            t = get_thumbnail(obj.image, '100x100', quality=80)
            return mark_safe('<img src="%s" />' % t.url)
        else:
            return ''

    preview.short_description = _('preview')  # type: ignore

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for f in ('teaser', 'text'):
            if not obj or obj.use_editor:
                # https://redmine.nastroyker.ru/issues/19241
                form.base_fields[f].widget = CKEditorWidget()
        return form


admin.site.register(News, NewsAdmin)
