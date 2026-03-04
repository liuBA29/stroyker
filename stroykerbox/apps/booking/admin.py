from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models


class ItemInline(admin.TabularInline):
    model = models.Item
    extra = 0


class HourRangeline(admin.TabularInline):
    model = models.ItemSetHourRange
    extra = 0


@admin.register(models.ItemSet)
class ItemSetAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'published')
    list_editable = ('published',)
    inlines = (ItemInline, HourRangeline)


class ItemReserveInline(admin.TabularInline):
    model = models.ItemReserve
    extra = 0


@admin.register(models.Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'itemset')
    list_filter = ('itemset',)
    search_fields = ('name',)
    inlines = (ItemReserveInline,)


@admin.register(models.ItemReserve)
class ItemReserveAdmin(admin.ModelAdmin):
    list_display = ('item', 'itemset', 'date', 'hour')
    list_filter = ('item__itemset', 'date', 'item')
    date_hierarchy = 'date'

    def itemset(self, obj=None):
        if obj:
            return obj.item.itemset.name
        return ''
    itemset.short_description = _('Набор')
