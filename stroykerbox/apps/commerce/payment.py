from logging import getLogger
import json

import binascii
import os
from collections import defaultdict
from django.urls import reverse
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _
from stroykerbox.settings.constants import BILLING_CONF_ITEMS, INVOICING, YOOKASSA
from constance import config
from yookassa import Payment as YookassaPaymentBase
from django.conf import settings

from stroykerbox.apps.catalog.models import Currency

from .forms import PaymentForm
from .models import YookassaData
from .utils import get_payment_methods_names
from .utils import update_yookassa_connect
from .signals import order_paid_by_yookassa

logger = getLogger('yookassa')


class YookassaPayment:
    _yookassa = None

    @property
    def yookassa(self):
        if not self._yookassa:
            update_yookassa_connect()
            self._yookassa = YookassaPaymentBase
        return self._yookassa

    def create(self, order):
        slug = binascii.hexlify(os.urandom(16)).decode()
        items = []
        currency = Currency.get_default().code.upper()
        for membership in order.order_products.all():
            items.append(
                {
                    'description': membership.product.name,
                    'quantity': membership.quantity,
                    'amount': {
                        'value': str(float(membership.personal_product_price)),
                        'currency': currency,
                    },
                    'vat_code': config.YOOKASSA_NDS_CODE,
                    'payment_subject': config.YOOKASSA_PAYMENT_SUBJECT,
                    'payment_mode': 'full_payment',
                }
            )

        customer = {}
        if order.user and order.user.email:
            customer['email'] = order.user.email
        elif hasattr(order, 'ordercontactdata') and order.ordercontactdata.email:
            customer['email'] = order.ordercontactdata.email
        elif getattr(order.delivery, 'email', None) and order.delivery.email:
            customer['email'] = order.delivery.email
        if hasattr(order, 'ordercontactdata') and order.ordercontactdata.name:
            customer['full_name'] = order.ordercontactdata.name
        elif order.user and (order.user.name or order.user.company or order.user.email):
            customer['full_name'] = (
                order.user.name or order.user.company or order.user.email
            )
        elif getattr(order.delivery, 'name', None) and order.delivery.name:
            customer['full_name'] = order.delivery.name
        if order.user and order.user.phone:
            customer['phone'] = order.user.phone
        elif hasattr(order, 'ordercontactdata') and order.ordercontactdata.phone:
            customer['phone'] = order.ordercontactdata.phone
        elif getattr(order.delivery, 'phone', None) and order.delivery.phone:
            customer['phone'] = order.delivery.phone
        request_create = {
            "amount": {"value": str(float(order.final_price)), "currency": currency},
            "confirmation": {
                "type": "redirect",
                "return_url": f"{settings.BASE_URL}%s"
                % (reverse('cart:yookassa_confirm', kwargs={'slug': slug})),
            },
            "capture": True,
            "description": f"Заказ №{order.pk}",
            "metadata": {'orderNumber': order.pk},
            "receipt": {"customer": customer, "items": items},
        }
        response_create = self.yookassa.create(request_create)
        YookassaData.objects.create(
            order=order,
            slug=slug,
            request_create=request_create,
            response_create=json.loads(response_create.json()),
            status=response_create['status'],
            yookassa_id=response_create['id'],
        )
        order.yookassa_status = response_create['status']
        order.save()
        return response_create['confirmation']['confirmation_url']

    def check_status(self, order, save=True):
        """Принудительно проверить все статусы, кроме отмененных"""
        statuses = set()
        update = defaultdict(list)
        for data in tuple(
            order.yookassadata_set.exclude(status=order.YOOKASSA_CANCELED)
        ):
            request = self.yookassa.find_one(data.yookassa_id)

            try:
                data_dict = json.loads(request.json())
                data.write_to_log(data_dict)
            except Exception as e:
                logger.exception(e)

            if save and data.status != request['status']:
                data.status = request['status']
                update[data.status].append(data.pk)
            if data.status != order.YOOKASSA_CANCELED:
                statuses.add(data.status)
        if save:
            for status, pks in update.items():
                YookassaData.objects.filter(pk__in=pks).update(status=status)
        status = order.YOOKASSA_CANCELED

        if order.YOOKASSA_SUCCEEDED in statuses:
            status = order.YOOKASSA_SUCCEEDED
        elif (
            order.YOOKASSA_PENDING in statuses or order.WAITING_FOR_CAPTURE in statuses
        ):
            status = order.YOOKASSA_PENDING
        if save and order.yookassa_status != status:
            logger.debug(
                f'Изменение статуса платежа через Yookassa для заказа {order}. '
                f'Предыдущий статус: {order.yookassa_status}. Новый статус: {status}'
            )
            order.yookassa_status = status
            order.save()
            if status == order.YOOKASSA_SUCCEEDED:
                try:
                    order_paid_by_yookassa.send(sender=order.__class__, order=order)
                except Exception as e:
                    logger.exception(e)
        return status


yookassa_payment = YookassaPayment()


class Payment:
    """
    Helper class for management user payment processing.
    """

    def __init__(self, order):
        self.order = order
        self.payment_methods_choices = get_payment_methods_names()
        self.available_payment_methods = order.delivery.available_payment_methods()

    def get_payment_select_form(self, data=None):
        pay_methods = []

        for method_index in self.available_payment_methods:
            index = int(method_index)
            # If there is not all necessary payment data,
            # then the invoice payment method is excluded.

            # if index == INVOICING and not self.check_invoicing_payment_data():
            #     continue
            pay_methods.append((index, self.payment_methods_choices.get(index, '')))

        return PaymentForm(data, choices=pay_methods, order=self.order)

    def check_invoicing_payment_data(self):
        """
        Check that exist all the necessary payment details of the recipient and of the customer.
        """
        if not self.order.user or not getattr(self.order.user, 'company', False):
            return False
        for item in BILLING_CONF_ITEMS:
            if item in ('BILLING_INFO__VAT', 'BILLING_INFO__SIGNATURE_FILE'):
                continue
            if not getattr(config, item, False):
                return False
        return True

    def process_payment(self, request, payment_method):
        if payment_method in self.payment_methods_choices.keys():
            if hasattr(self.order, 'payment_method') and (
                self.order.payment_method != payment_method
            ):
                self.order.payment_method = payment_method
                if payment_method == INVOICING:
                    self.order.invoicing_with_vat = 'invoicing_with_vat' in request.POST
                self.order.save()
        else:
            messages.add_message(request, messages.ERROR, _('Unknown payment method'))
            return redirect(reverse('cart:failed'))

        if (
            hasattr(self.order, 'payment_method')
            and self.order.payment_method == YOOKASSA
        ):
            return redirect(yookassa_payment.create(self.order))
        return redirect(reverse('cart:success'))
