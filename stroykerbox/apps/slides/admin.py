from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from sorl.thumbnail import get_thumbnail
from stroykerbox.apps.custom_forms.utils import custom_form_help_text

from .models import BigSlide, PartnerSlide, SliderSet, SliderSetItem


@admin.register(BigSlide)
class BigSlideAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'preview', 'position', 'published')
    list_editable = ('position', 'published')

    def preview(self, obj):
        if obj.image:
            try:
                thumb = get_thumbnail(obj.image, '100x100', quality=80)
            except IOError as e:
                return 'Image error: %s' % str(e)
            else:
                return format_html('<img src="%s" />' % thumb.url)
        return ''

    preview.short_description = _('preview')
    preview.allow_tags = True


@admin.register(PartnerSlide)
class PartnerSlideAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'preview')

    def preview(self, obj):
        if obj.logo:
            try:
                thumb = get_thumbnail(obj.logo, '100x100', quality=80)
            except IOError as e:
                return 'Image error: %s' % str(e)
            else:
                return format_html('<img src="%s" />' % thumb.url)
        return ''

    preview.short_description = _('preview')
    preview.allow_tags = True


class SliderSetItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].help_text += custom_form_help_text

    class Meta:
        model = SliderSetItem
        exclude = ()


class SliderSetItemInline(admin.StackedInline):
    model = SliderSetItem
    form = SliderSetItemForm
    extra = 0


@admin.register(SliderSet)
class SliderSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'key')
    inlines = (SliderSetItemInline,)
