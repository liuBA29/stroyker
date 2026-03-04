from django.contrib import admin
from django.utils.translation import ugettext as _
from django.db.models import JSONField
from django.http import HttpResponseRedirect
from django.urls import path, reverse

from stroykerbox.apps.utils.widgets import JSONEditorWidget

from .models import SubcategoryAsParameter, TicketStock, UpdateLog
from .tbank.models import TBankPayment


@admin.register(TBankPayment)
class TBankPaymentAdmin(admin.ModelAdmin):
    list_display = ('payment_id', 'order_id', 'created_at', 'status')
    readonly_fields = ('payment_id', 'order_id', 'created_at', 'status', 'payment_url')
    formfield_overrides = {JSONField: {'widget': JSONEditorWidget}}
    change_form_template = 'smartlombard/tbank/admin/tbankpayment_change_form.html'

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'payment_id',
                    'order_id',
                    'created_at',
                    'status',
                    'payment_url',
                ),
            },
        ),
        (
            'Логи',
            {
                'classes': ('collapse',),
                'fields': ('log',),
            },
        ),
    )

    def has_add_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        return [
            path(
                'update_payment_status/<str:payment_id>/',
                self.update_payment_status,
                name='update_payment_status',
            ),
        ] + urls

    def update_payment_status(self, request, payment_id: str):
        payment = self.get_object(request, payment_id)
        if payment.update_payment_status():
            self.message_user(
                request,
                ('Данные успешно обновлены. Результат запроса записан в лог платежа.'),
                'INFO',
            )
        else:
            self.message_user(
                request, 'При обновлении данных возникли ошибки.', 'ERROR'
            )

        return HttpResponseRedirect(
            reverse('admin:smartlombard_tbankpayment_change', args=[payment_id])
        )


@admin.register(SubcategoryAsParameter)
class SubcategoryAsParameterAdmin(admin.ModelAdmin):
    list_display = ('parent_category', 'parameter')


@admin.register(TicketStock)
class TicketStockAdmin(admin.ModelAdmin):
    list_display = ('code', 'stock_address')

    def stock_address(self, obj):
        return obj.stock.address

    stock_address.short_description = _('stock address')  # type: ignore


@admin.register(UpdateLog)
class UpdateLogAdmin(admin.ModelAdmin):
    list_display = ('created', 'last_entry')
    date_hierarchy = 'created'

    def last_entry(self, obj):
        try:
            return obj.log[-1]
        except Exception:
            pass
        return ''

    last_entry.short_description = _('last entry')  # type: ignore
