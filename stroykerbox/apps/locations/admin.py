from django.contrib import admin
from django.apps import apps
from django_geoip.models import City

from .models import Location, LocationPhone


class LocationPhoneInline(admin.TabularInline):
    model = LocationPhone
    extra = 0


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    search_fields = ('name',)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'slug', 'is_default', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    inlines = (LocationPhoneInline,)
    autocomplete_fields = ('city',)
    search_fields = ('name',)

    def delete_queryset(self, request, queryset):
        CrmRequestBase = apps.get_model('crm.CrmRequestBase')

        for obj in queryset:
            CrmRequestBase.objects.filter(location=obj).update(location=None)

        queryset.delete()
