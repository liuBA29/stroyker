from django.contrib import admin
from django.db.models import JSONField
from import_export.admin import ExportMixin

from stroykerbox.apps.utils.widgets import PrettyJSONWidget

from .models import SearchQueryData, SearchWordAlias


@admin.register(SearchQueryData)
class SearchQueryDataAdmin(ExportMixin, admin.ModelAdmin):
    formfield_overrides = {JSONField: {'widget': PrettyJSONWidget}}
    list_display = ('query', 'created_at', 'user')
    search_fields = ('query',)
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False


@admin.register(SearchWordAlias)
class SearchWordAliasAdmin(admin.ModelAdmin):
    pass
