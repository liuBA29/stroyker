# type: ignore
from typing import Optional

import django
from django.contrib import admin
from django.db import models
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import force_text
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.timezone import now
from django.shortcuts import get_object_or_404, render
from django.conf import settings
from django.db.models import JSONField
from constance import config

from stroykerbox.apps.commerce import models as commerce_models
from stroykerbox.apps.locations.models import Location
from stroykerbox.settings.constants import INVOICING
from stroykerbox.apps.utils.widgets import JSONEditorWidget

from .import_export import get_order_export_data
from .payment import yookassa_payment


@admin.register(commerce_models.TransportCompany)
class TransportCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'delivery_price')


@admin.register(commerce_models.DeliveryCar)
class TruckAdmin(admin.ModelAdmin):
    list_display = ('name', 'position')
    list_editable = ('position',)
    list_filter = ('location',)


@admin.register(commerce_models.OrderContactData)
class OrderContactDataAdmin(admin.ModelAdmin):
    list_display = ['order', 'name']


class OrderProductMembershipInline(admin.TabularInline):
    model = commerce_models.OrderProductMembership
    raw_id_fields = ('product',)
    extra = 0


class OrderContactDataInline(admin.TabularInline):
    model = commerce_models.OrderContactData

    def has_delete_permission(self, request, obj=None):
        return False


class OrderAdminForm(forms.ModelForm):
    class Meta:
        model = commerce_models.Order
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Include only the current status and all possible further statuses.
        self.fields['status'].choices = [
            (k, v)
            for k, v in self.fields['status'].choices
            if (
                k == self.instance.status
                or k
                in commerce_models.STATUS_TO_CLASS_MAPPER[
                    self.instance.status
                ].POSSIBLE_STATUS_CHOICES
            )
        ]

        if 'delivery_type' in self.fields:
            delivery_choices = []
            for ch0, ch1 in self.fields['delivery_type'].choices:
                if ch0:
                    ch1 = ch0.instance.model_class().get_display_name()
                delivery_choices.append((ch0, ch1))

            self.fields['delivery_type'].choices = delivery_choices


class OrderAdminFormCommentRequired(OrderAdminForm):
    def __init__(self, *args, **kwargs):
        super(OrderAdminFormCommentRequired, self).__init__(*args, **kwargs)
        self.fields['comment'].required = True


class ExcludeStatusListFilter(admin.SimpleListFilter):
    title = _('exclude status')
    parameter_name = 'status'

    DEFAULT_VALUE = 'draft'

    def lookups(self, request, model_admin):
        return commerce_models.Order.STATUS_CHOICES + (('show_all', _('Show all')),)

    def queryset(self, request, queryset):
        value = self.value() or self.DEFAULT_VALUE
        if value == 'show_all':
            return queryset
        else:
            return queryset.exclude(status=value)

    def choices(self, cl):
        for lookup, title in self.lookup_choices:
            lookup_text = force_text(lookup)
            yield {
                'selected': lookup_text == self.value()
                or (self.value() is None and lookup_text == self.DEFAULT_VALUE),
                'query_string': cl.get_query_string(
                    {
                        self.parameter_name: lookup,
                    },
                    [],
                ),
                'display': title,
            }


@admin.register(commerce_models.YookassaData)
class YookassaDataAdmin(admin.ModelAdmin):
    list_display = list_display_links = ('order', 'slug', 'status', 'created')
    readonly_fields = (
        'order',
        'created',
        'slug',
        'yookassa_id',
        'status',
    )
    formfield_overrides = {JSONField: {'widget': JSONEditorWidget}}
    change_form_template = 'commerce/admin/yookassadata_change_form.html'
    fieldsets = [
        (
            None,
            {
                'fields': ['order', 'slug', 'yookassa_id', 'created', 'status'],
            },
        ),
        (
            'Логи',
            {
                'classes': ['collapse'],
                'fields': ['log', 'request_create', 'response_create'],
            },
        ),
    ]

    def change_view(
        self, request, object_id, form_url="", extra_context: Optional[dict] = None
    ):
        extra_context = extra_context or dict()
        extra_context['yookassa_not_check_statuses'] = (
            commerce_models.Order.YOOKASSA_SUCCEEDED,
            commerce_models.Order.YOOKASSA_CANCELED,
        )
        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context=extra_context,
        )

    def get_urls(self):
        urls = super().get_urls()
        return [
            path(
                'update_payment_status/<int:yookassa_payment_pk>/',
                self.update_payment_status,
                name='update_payment_status',
            ),
        ] + urls

    def update_payment_status(self, request, yookassa_payment_pk: int):
        payment = self.get_object(request, yookassa_payment_pk)
        if yookassa_payment.check_status(payment.order):
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
            reverse('admin:commerce_yookassadata_change', args=[yookassa_payment_pk])
        )


class YookassaDataInline(admin.StackedInline):
    model = commerce_models.YookassaData
    extra = 0
    readonly_fields = (
        'created',
        'slug',
        'yookassa_id',
        'request_create',
        'response_create',
        'status',
    )


@admin.register(commerce_models.Order)
class OrderAdmin(admin.ModelAdmin):
    form = OrderAdminForm
    change_list_template = 'commerce/admin/order_changelist.html'
    change_form_template = 'commerce/admin/order_change_form.html'

    def get_urls(self):
        new_url = [
            path('order_export/', self.order_export, name='order_export'),
            path('order_print/<int:order_pk>/', self.order_print, name='order_print'),
        ]
        return new_url + super().get_urls()

    def extra_fields_display(self, obj):
        """Отображение OrderExtraFieldValue в виде таблицы"""
        extra_values = commerce_models.OrderExtraFieldValue.objects.filter(order=obj)

        if not extra_values.exists():
            return 'Нет дополнительных полей'

        html = "<table style='width:100%; border: 1px solid #ccc; text-align: left;'>"
        html += '<tr >'

        # Заголовки
        for field_value in extra_values:
            html += (
                "<th style='padding:5px; border-bottom: 1px solid #ccc;'>"
                f"{field_value.field.label or field_value.field.name}</th>"
            )
        html += '</tr><tr>'

        # Значения
        for field_value in extra_values:
            html += f"<td style='padding:5px; border-bottom: 1px solid #ccc;'>{field_value.value}</td>"
        html += '</tr></table>'

        return mark_safe(html)

    extra_fields_display.short_description = 'Дополнительные поля'

    @staticmethod
    def order_print(request, order_pk):
        order = get_object_or_404(commerce_models.Order, pk=order_pk)
        context = {
            'order': order,
            'region': Location.get_default_location(),
            'host': settings.BASE_URL.split('//')[-1],
            'products': commerce_models.OrderProductMembership.objects.filter(
                order=order
            ),
        }
        return render(request, 'commerce/admin/order-print-form.html', context)

    def get_export_queryset(self, request):
        """
        Returns export queryset.

        Default implementation respects applied search and filters.
        """
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        list_select_related = self.get_list_select_related(request)
        list_filter = self.get_list_filter(request)
        search_fields = self.get_search_fields(request)
        if self.get_actions(request):
            list_display = ['action_checkbox'] + list(list_display)

        ChangeList = self.get_changelist(request)
        changelist_kwargs = {
            'request': request,
            'model': self.model,
            'list_display': list_display,
            'list_display_links': list_display_links,
            'list_filter': list_filter,
            'date_hierarchy': self.date_hierarchy,
            'search_fields': search_fields,
            'list_select_related': list_select_related,
            'list_per_page': self.list_per_page,
            'list_max_show_all': self.list_max_show_all,
            'list_editable': self.list_editable,
            'model_admin': self,
        }
        changelist_kwargs['sortable_by'] = self.sortable_by
        if django.VERSION >= (4, 0):
            changelist_kwargs['search_help_text'] = self.search_help_text
        cl = ChangeList(**changelist_kwargs)

        return cl.get_queryset(request)

    def order_export(self, request):
        try:
            qs = self.get_export_queryset(request)
            data = get_order_export_data(qs, 'xls')
            filename = f'order_export_{now().strftime("%Y-%m-%d")}.xls'

            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename={filename}'
            response.write(data)
            return response
        except Exception as e:
            self.message_user(request, 'Ошибка экспорта.', 'ERROR')
            self.message_user(request, e, 'ERROR')

        return HttpResponseRedirect(reverse('admin:commerce_order_changelist'))

    def get_exclude(self, request, obj=None):
        fields = ['status_changed_at', 'location', 'extra_fields_display']
        if config.SIMPLE_CART_MODE:
            fields += ['delivery_type', 'delivery_id']
            if getattr(obj, 'payment_method', '') == '':
                fields.append('payment_method')
        return fields

    def get_form(self, request, obj=None, **kwargs):
        if request.POST.get('status') == 'cancelled':
            kwargs['form'] = OrderAdminFormCommentRequired
        return super(OrderAdmin, self).get_form(request, obj, **kwargs)

    def delivery_link(self, obj):
        if getattr(obj, 'delivery', None):
            model_name = type(obj.delivery).__name__.lower()
            if model_name == 'statictext':
                obj.delete()
                return
            url = reverse(
                'admin:commerce_{model_name}_change'.format(model_name=model_name),
                args=(obj.delivery_id,),
            )
            return mark_safe(
                '<a href="{url}">{text}</a>'.format(url=url, text=_('delivery details'))
            )
        else:
            return ''

    delivery_link.short_description = _('delivery details')

    def user_link(self, obj):
        if obj.user:
            model_name = type(obj.user).__name__.lower()
            url = reverse(
                'admin:users_{model_name}_change'.format(model_name=model_name),
                args=(obj.user.id,),
            )
            return mark_safe(
                '<a href="{url}">{text}</a>'.format(url=url, text=_('user details'))
            )
        else:
            return ''

    user_link.short_description = _('user details')

    def user_name(self, obj):
        if obj.user:
            return obj.user.get_username()
        return _('Anonymous user')

    def order_location(self, obj):
        if not obj.location:
            return _('Default')
        return obj.location.city

    def invoice_pdf(self, obj):
        if obj and obj.payment_method == INVOICING:
            text = _('Download invoice')
            url = reverse('cart:order-invoice-pdf', args=(obj.pk,))
            return mark_safe(f'<a href="{url}" download>{text}</a>')
        else:
            return ''

    invoice_pdf.short_description = _('Invoice PDF')

    def get_readonly_fields(self, request, obj=None):
        fields = []
        if obj:
            if obj.delivery:
                fields.append('delivery_type_name')
            if obj.payment_method == INVOICING:
                fields.append('invoice_pdf')
            fields.append('extra_fields_display')  # Qo‘shilgan qism

        return fields

    user_name.short_description = _('user name')
    user_name.allow_tags = True

    list_display = (
        'pk',
        'user_name',
        'delivery_type_name',
        'final_price',
        'is_paid',
        'status',
        'created_at',
        'delivery_link',
        'user_link',
        'order_location',
    )
    search_fields = ('id',)
    list_filter = (
        ExcludeStatusListFilter,
        'status_changed_at',
        'delivery_type',
        'created_at',
        'status',
    )
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'

    formfield_overrides = {
        models.ManyToManyField: {'widget': forms.CheckboxSelectMultiple},
    }

    def delivery_type_name(self, obj=None):
        if getattr(obj, 'delivery', None):
            return str(obj.delivery)
        return ''

    delivery_type_name.short_description = _('Доставка')

    def get_inline_instances(self, request, obj=None):
        self.inlines = []
        if config.SIMPLE_CART_MODE:
            self.inlines.append(OrderContactDataInline)
        self.inlines.extend([OrderProductMembershipInline, YookassaDataInline])
        return super().get_inline_instances(request, obj)


@admin.register(commerce_models.ToAddressDelivery)
class ToAddressDeliveryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone', 'email', 'address')


admin.site.register(commerce_models.PickUpDelivery)
admin.site.register(commerce_models.ToTCDelivery)


@admin.register(commerce_models.OrderExtraField)
class OrderExtraFieldAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'required', 'binded_to')
    list_filter = ('binded_to', 'required')


@admin.register(commerce_models.OrderExtraFieldValue)
class OrderExtraFieldValueAdmin(admin.ModelAdmin):
    list_display = ('order', 'field')
