from django import forms
from django.contrib import admin

from stroykerbox.apps.banners import models
from stroykerbox.apps.custom_forms.utils import custom_form_help_text


class BannerDisplayUrlInline(admin.TabularInline):
    model = models.BannerDisplayUrl
    extra = 0


@admin.register(models.Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date',
                    'clicks_counter', 'views_counter', 'position')
    inlines = (BannerDisplayUrlInline,)
    readonly_fields = ('clicks_counter', 'views_counter',
                       'renewal_notice_date')
    list_editable = ('position',)


class BannerSetItemInline(admin.TabularInline):
    model = models.BannerSetRowItem
    extra = 0


@admin.register(models.BannerSet)
class BannerSetAdmin(admin.ModelAdmin):
    inlines = (BannerSetItemInline,)

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and hasattr(obj, 'key'):
            return ('key',)
        return super().get_readonly_fields(request, obj=None)


class StroykerBannerDisplayUrlInline(admin.TabularInline):
    model = models.StroykerBannerDisplayUrl
    extra = 0


@ admin.register(models.StroykerBanner)
class StroykerBannerAdmin(BannerAdmin):
    inlines = (StroykerBannerDisplayUrlInline,)


class BannerRowItemForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].help_text += custom_form_help_text

    class Meta:
        model = models.BannerRowItem
        exclude = ()


class BannerRowItemInline(admin.StackedInline):
    form = BannerRowItemForm
    model = models.BannerRowItem
    extra = 0


@admin.register(models.BannerRowSet)
class BannerRowSetAdmin(admin.ModelAdmin):
    list_display = ('row_name', 'row_type')
    inlines = (BannerRowItemInline,)

    def row_name(self, obj):
        if obj:
            return str(obj)
        return ''


class BannerMultirowSetRowsInline(admin.TabularInline):
    model = models.BannerMultirowSetRows
    extra = 0


@admin.register(models.BannerMultirowSet)
class BannerMultirowSetAdmin(admin.ModelAdmin):
    inlines = (BannerMultirowSetRowsInline,)

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and hasattr(obj, 'key'):
            return ('key',)
        return super().get_readonly_fields(request, obj=None)
