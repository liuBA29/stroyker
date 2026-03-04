from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from .models import Menu, MenuItem, CustomNavigation, CustomLink


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    verbose_name = _('menu item')
    verbose_name_plural = _('menu items')
    extra = 0

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('position',)


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('title', 'key')
    inlines = (MenuItemInline, )

    def get_readonly_fields(self, request, obj=None):
        if hasattr(obj, 'key'):
            return ('key',)
        else:
            return super().get_readonly_fields(request, obj)


class CustomLinkInline(admin.TabularInline):
    model = CustomLink
    extra = 0
    sortable_field_name = 'position'


@admin.register(CustomNavigation)
class CustomNavigationAdmin(admin.ModelAdmin):
    list_display = ('title', 'comment')
    inlines = [CustomLinkInline]
    readonly_fields = ('key',)
