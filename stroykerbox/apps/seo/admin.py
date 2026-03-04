from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from .models import RobotsTxt, MetaTag
from .resources import MetaTagBaseResource


@admin.register(RobotsTxt)
class RobotsTxtAdmin(admin.ModelAdmin):
    list_display = ('site',)


@admin.register(MetaTag)
class MetaTagAdmin(ImportExportModelAdmin):
    list_display = ('url', 'title')
    ordering = ('url',)
    search_fields = ('url',)
    resource_class = MetaTagBaseResource
