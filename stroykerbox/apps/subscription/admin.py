from django.contrib import admin

from import_export.admin import ExportActionMixin
from import_export import resources

from .models import Subscription


class SubscriptionResource(resources.ModelResource):
    class Meta:
        model = Subscription
        fields = ('email', 'created_at')


@admin.register(Subscription)
class SubscriptionAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_class = SubscriptionResource
    list_display = ('email', 'created_at')
