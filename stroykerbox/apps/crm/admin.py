import os

from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.urls import path, reverse
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse

from import_export import resources
from import_export.admin import ExportMixin
from import_export.fields import Field

from stroykerbox.apps.common.utils import get_logfile_content
from stroykerbox.apps.api.crm.serializers import CrmRequestBaseSerializer
from stroykerbox.apps.common.utils import send_json_to_url

from .models import CrmRequestBase


class CRMExportResource(resources.ModelResource):
    email = Field(column_name='email')
    msg_type = Field(column_name='message type')

    class Meta:
        model = CrmRequestBase
        fields = ('name', 'phone', 'email', 'message', 'msg_type', 'created')
        export_order = fields

    def dehydrate_email(self, msg):
        email = getattr(msg, 'email', None)
        if not email and msg.order:
            if hasattr(msg.order, 'ordercontactdata'):
                email = msg.order.ordercontactdata.email
            elif hasattr(msg.order, 'user'):
                email = getattr(msg.order.user, 'email', None)
        return email or ''

    def dehydrate_msg_type(self, msg):
        obj = msg.get_object()
        return obj._meta.verbose_name


@admin.register(CrmRequestBase)
class CrmRequestBaseAdmin(ExportMixin, admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'request_type',
        'created',
        'changed',
        'status',
        'delivery_type',
        'payment_type',
        'order_final_price',
        'order_is_paid',
        'phone',
        'name',
        'manager_comment',
        'manager',
        'location',
    )
    exclude = ('object_class',)

    resource_class = CRMExportResource
    change_list_template = 'crm/admin/crmrequestbase_changelist.html'
    change_form_template = 'crm/admin/crmrequestbase_change_form.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'crm-cf-notify-log/',
                self.crm_cf_notify_log,
                name='crm-cf-notify-log',
            ),
            path(
                'send-crm-cf-notify/<int:crm_obj_pk>/',
                self.send_crm_cf_notify,
                name='send-crm-cf-notify',
            ),
        ]
        return custom_urls + urls

    def send_crm_cf_notify(self, request, crm_obj_pk: int):
        try:
            obj = CrmRequestBase.objects.get(pk=crm_obj_pk)
        except CrmRequestBase.DoesNotExist:
            self.message_user(request, f'Объект с ID {crm_obj_pk} не найден.', 'ERROR')
        else:
            serializer = CrmRequestBaseSerializer(obj)
            result_msg = send_json_to_url(serializer.data, timeout=5)
            msg_type = 'ERROR' if 'FAIL' in result_msg else 'SUCCESS'

        self.message_user(request, result_msg, msg_type)

        return HttpResponseRedirect(
            reverse('admin:crm_crmrequestbase_change', args=[crm_obj_pk])
        )

    def crm_cf_notify_log(self, request) -> HttpResponse:
        filename = settings.CRM_CF_JSON_NOTIFY_LOG_FILENAME
        output = get_logfile_content(filename)
        context = {'text': output, 'log_file': os.path.join(settings.LOG_DIR, filename)}
        return render(request, 'crm/admin/crm_json_notify_log.html', context)

    def request_type(self, obj):
        return obj._meta.verbose_name

    def get_readonly_fields(self, request, obj=None):
        fields = list(self.readonly_fields)
        if hasattr(obj, 'email'):
            fields += ['email']
        if hasattr(obj, 'url'):
            fields += ['url']
        return fields

    def email(self, obj):
        return getattr(obj, 'email')

    def url(self, obj):
        return getattr(obj, 'url')

    def delivery_type(self, obj):
        if obj.order is not None:
            return obj.order.delivery

    def payment_type(self, obj):
        if obj.order is not None:
            return obj.order.payment_method_name

    def order_final_price(self, obj):
        if obj.order is not None:
            return obj.order.final_price

    def order_is_paid(self, obj):
        if obj.order is not None:
            return _('yes') if obj.order.is_paid else _('no')

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()
