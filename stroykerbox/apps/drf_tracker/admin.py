from io import StringIO

from django.contrib import admin
from django.db.models import JSONField, TextField
from django.urls import path, reverse
from django.core.management import call_command
from django.http import HttpResponseRedirect

from stroykerbox.apps.utils.widgets import PrettyJSONWidget

from .models import APIRequestLog


@admin.register(APIRequestLog)
class APIRequestLogAdmin(admin.ModelAdmin):
    list_display = (
        'requested_at',
        'path',
        'status_code',
        'method',
    )
    search_fields = ('path',)
    ordering = ('-requested_at',)
    list_filter = ('method', 'status_code')
    date_hierarchy = 'requested_at'

    json_field_data = {'widget': PrettyJSONWidget(attrs=dict(readonly=True))}
    formfield_overrides = {
        JSONField: json_field_data,
        TextField: json_field_data,
    }

    readonly_fields = (
        'user',
        'requested_at',
        'response_ms',
        'path',
        'view',
        'view_method',
        'remote_addr',
        'host',
        'method',
        'errors',
        'status_code',
        'user_agent',
    )
    change_list_template = 'drf_tracker/admin/apirequestlog_change_list.html'

    def get_urls(self):
        urls = super().get_urls()
        app_urls = [
            path(
                'clear-all',
                self.clear_all,
                name='api-clear-logs-all',
            ),
        ]
        return app_urls + urls

    def clear_all(self, request):
        stdout, stderr = StringIO(), StringIO()
        call_command('clearapilogs', '--no-color', stdout=stdout, stderr=stderr)

        if err_msg := stderr.getvalue():
            self.message_user(request, err_msg, 'ERROR')

        if msg := stdout.getvalue():
            self.message_user(request, msg, 'INFO')

        return HttpResponseRedirect(
            reverse('admin:drf_tracker_apirequestlog_changelist')
        )

    def has_add_permission(self, request):
        return False
