import json
from decimal import Decimal
from unittest import mock

from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest, HttpResponseRedirect
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail

import django_rq
from model_bakery import baker
from constance.test import override_config
from stroykerbox.apps.commerce import models, payment, tasks
from stroykerbox.apps.commerce.cart import Cart
from stroykerbox.settings import constants

from .test_cart import CartGenericTest


class OrderGenericTest(CartGenericTest):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.session = self.client.session
        with mock.patch('stroykerbox.apps.catalog.models.Product.is_available',
                        return_value=True):
            self.user_cart.add_product(self.product1)
        self.user_cart.save_to_session(self.session)
        delivery = baker.make(models.PickUpDelivery)
        self.order = baker.make(models.Order, user=self.user, delivery=delivery,
                                total_price=self.user_cart.total_price)
        self.user_cart.order = self.order
        self.user_cart.save_to_session(self.session)
        self.session.save()

        self.order_payment = payment.Payment(self.order)
        self.worker = django_rq.get_worker('default')


class OrderDeliveryTest(OrderGenericTest):

    def test_delivery_page_available(self):
        response = self.client.get(reverse('cart:delivery'))
        self.assertEqual(200, response.status_code)

    def test_delivery_page_empty_cart(self):
        self.client.logout()
        response = self.client.get(reverse('cart:delivery'))
        # redirect on cart page
        self.assertEqual(302, response.status_code)

    def test_cart_order_on_delivery_page(self):
        order = baker.make(models.Order, user=self.user)
        self.user_cart.order = order
        self.user_cart.save_to_session(self.session)
        self.session.save()
        delivery_type = ContentType.objects.get_for_model(
            models.PickUpDelivery)
        response = self.client.post(reverse('cart:delivery'), {
                                    'delivery_type': delivery_type.id})
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.context['form'].is_valid())


@override_config(BILLING_INFO__BANK__NAME='bank name', BILLING_INFO__BANK__BIK='bik',
                 BILLING_INFO__BANK__ACC_NUM='num', BILLING_INFO__NAME='info name',
                 BILLING_INFO__INN='inn', BILLING_INFO__KPP='kpp',
                 BILLING_INFO__COMPANY_BANK_ACC_NUM='acc num', BILLING_INFO__ADDRESS='address')
class OrderPaymentTest(OrderGenericTest):

    def test_payment_page_available(self):
        response = self.client.get(reverse('cart:payment'))
        self.assertEqual(200, response.status_code)

    def test_payment_page_with_empty_cart(self):
        self.client.logout()
        response = self.client.get(reverse('cart:payment'))
        self.assertEqual(302, response.status_code)

    def test_payment_class_check_invoicing_payment_data(self):
        # company name is not set for the order user
        self.assertFalse(self.order_payment.check_invoicing_payment_data())
        # fixing it
        self.user.company = 'some company name'
        self.user.save()
        self.assertTrue(self.order_payment.check_invoicing_payment_data())
        # anonymous verification fails
        self.order.user = None
        self.order.save()
        order_payment = payment.Payment(self.order)
        self.assertFalse(order_payment.check_invoicing_payment_data())

    def test_payment_class_process_payment(self):

        request = HttpRequest()
        setattr(request, 'session', 'session')
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)

        # with success
        # <HttpResponseRedirect
        # status_code=302, "text/html; charset=utf-8", url="/cart/success/">
        success_method = self.order_payment.process_payment(
            request, constants.CARD_UPON_RECEIPT)
        self.assertIsInstance(success_method, HttpResponseRedirect)
        self.assertEqual(success_method.status_code, 302)
        self.assertEqual(success_method.url, reverse('cart:success'))
        # with failed (unknown payment method)
        # <HttpResponseRedirect
        # status_code=302, "text/html; charset=utf-8", url="/cart/failed/">
        wrong_method = self.order_payment.process_payment(
            request, 999)
        self.assertIsInstance(wrong_method, HttpResponseRedirect)
        self.assertEqual(wrong_method.status_code, 302)
        self.assertEqual(wrong_method.url, reverse('cart:failed'))

    def test_payment_select_form(self):
        response = self.client.post(reverse('cart:payment'),
                                    {'payment_method': constants.CARD_UPON_RECEIPT})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart:success'))

    def test_payment_page_without_order(self):
        """
        If the cart has no the order then redirect to the delivery checkout page.
        """
        self.user_cart.order = None
        self.user_cart.save_to_session(self.session)
        self.session.save()
        response = self.client.get(reverse('cart:payment'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart:delivery'))


class OrderNotifyTest(OrderGenericTest):

    def test_new_order_notify_customer(self):
        with mock.patch('stroykerbox.apps.commerce.tasks.new_order_notify_customer.delay') as patch_mock:
            self.client.get(reverse('cart:success'))
        self.assertTrue(patch_mock.called)
        self.assertEqual(len(mail.outbox), 0)
        tasks.new_order_notify_customer(self.order.pk)
        self.assertEqual(len(mail.outbox), 1)

    def test_new_order_notify_customer_with_invoicing(self):
        with mock.patch('stroykerbox.apps.commerce.tasks.OrderNotify.with_invoicing') as patch_mock:
            patch_mock.return_value = True
            tasks.new_order_notify_customer(self.order.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].attachments[0][2], 'application/pdf')

    @override_config(MANAGER_EMAILS='manager1@mail.localhost, manager2@mail.localhost')
    def test_new_order_notify_managers(self):
        with mock.patch('stroykerbox.apps.commerce.tasks.new_order_notify_manager.delay') as patch_mock:
            self.client.get(reverse('cart:success'))
        self.assertTrue(patch_mock.called)
        self.assertEqual(len(mail.outbox), 0)
        tasks.new_order_notify_manager(self.order.pk)
        self.assertEqual(len(mail.outbox), 1)

    @override_config(MANAGER_EMAILS='manager1@mail.localhost, manager2@mail.localhost')
    def test_new_order_with_new_user_registration(self):
        """
        If the order user is anonymous, then this user is hiddenly registered,
        and a notification about the new registration is sent to the manager.
        """
        self.order.user = None
        self.order.save()
        with mock.patch('stroykerbox.apps.users.tasks.new_registration_notify_manager.delay') as patch_mock:
            self.client.get(reverse('cart:success'))
        self.assertTrue(patch_mock.called)
        # Checking the sending of the notification itself.
        # Regardless of the order.
        tasks.new_order_notify_manager(self.order.pk)
        self.assertEqual(len(mail.outbox), 1)


@mock.patch('stroykerbox.apps.catalog.models.Product.is_available', return_value=True)
class OrderAjaxViewsTest(OrderGenericTest):
    def setUp(self):
        super().setUp()
        self.car = models.DeliveryCar.objects.create(
            name='some_car_model',
            carrying=1500,
            volume=30.5,
            store_start_cost=230,
            cost_km=150,
        )

    def test_ajax_delivery_to_address_cost(self, _):
        """
        FORMULAS:
        delivery_cost = round(route_length_km * car.cost_km)
        if car.store_start_cost(default is 0):
            delivery_cost += car.store_start_cost
        cost_with_delivery = self.cart.total_price + delivery_cost
        """
        route_length_km = 22
        url = reverse('cart:ajax_get_delivery_to_address_cost')
        response = self.client.get(url, {'car_pk': self.car.pk,
                                         'route_length_km': route_length_km},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

        content = json.loads(response.content)

        self.assertEqual(content['success'], True)
        self.assertEqual(Decimal(content['delivery_cost']),
                         (Decimal(self.car.cost_km * route_length_km) + Decimal(self.car.store_start_cost)))  # noqa
        self.assertEqual(Decimal(content['cost_with_delivery']),
                         (self.user_cart.total_price + Decimal(content['delivery_cost'])))

    def test_ajax_delivery_to_address_cost_with_wrong_car(self, _):
        route_length_km = 22
        wrong_car_pk = 382932
        url = reverse('cart:ajax_get_delivery_to_address_cost')
        response = self.client.get(url, {'car_pk': wrong_car_pk,
                                         'route_length_km': route_length_km},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 404)

    def test_ajax_delivery_to_tc_cost(self, _):
        """
        tc - Transport company model object

        FORMULAS:
        delivery_cost = tc.delivery_price
        cost_with_delivery = self.cart.total_price + delivery_cost
        """
        tc = baker.make(models.TransportCompany, delivery_price=328)
        url = reverse('cart:ajax_get_delivery_to_tc_cost')
        response = self.client.get(url, {'tc_pk': tc.pk},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

        content = json.loads(response.content)

        self.assertEqual(content['success'], True)
        self.assertEqual(
            Decimal(content['delivery_cost']), Decimal(tc.delivery_price))
        self.assertEqual(Decimal(content['cost_with_delivery']),
                         (self.user_cart.total_price + Decimal(content['delivery_cost'])))

    def test_ajax_delivery_to_tc_cost_with_wrong_tc(self, _):
        wrong_tc_pk = 2398923
        url = reverse('cart:ajax_get_delivery_to_tc_cost')
        response = self.client.get(url, {'tc_pk': wrong_tc_pk},
                                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 404)


class OrderCommonTest(OrderGenericTest):
    def test_success_page_without_order(self):
        """
        If the cart has no the order then redirect to the delivery checkout page.
        """
        self.user_cart.order = None
        self.user_cart.save_to_session(self.session)
        self.session.save()
        response = self.client.get(reverse('cart:success'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart:delivery'))

    def test_confirm_page_without_order(self):
        """
        If the cart has no the order then redirect to the delivery checkout page.
        """
        self.user_cart.order = None
        self.user_cart.save_to_session(self.session)
        self.session.save()
        response = self.client.get(reverse('cart:confirm'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart:delivery'))

    def test_confirm_page_without_payment_method(self):
        self.user_cart.order.payment_method = None
        self.user_cart.order.save()
        self.user_cart.save_to_session(self.session)
        self.session.save()
        response = self.client.get(reverse('cart:confirm'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('cart:payment'))

    def test_confirm_page_with_all_right(self):
        self.user_cart.order.payment_method = constants.CARD_UPON_RECEIPT
        self.user_cart.order.save()
        self.user_cart.save_to_session(self.session)
        self.session.save()
        response = self.client.get(reverse('cart:confirm'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/confirm.html')
        self.assertIsInstance(response.context['cart'], Cart)

    def test_failed_page(self):
        response = self.client.get(reverse('cart:failed'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'cart/failed.html')
        self.assertIsInstance(response.context['order'], models.Order)

        # without order
        self.user_cart.order = None
        self.user_cart.save_to_session(self.session)
        self.session.save()
        response = self.client.get(reverse('cart:failed'))
        self.assertEqual(response.status_code, 404)

    def test_order_invoice_pdf_generation_with_fails(self):
        url = reverse('cart:order-invoice-pdf',
                      kwargs={'order_pk': self.order.pk})
        response = self.client.get(url)
        # User has no access to this page. Redirect to the login page.
        self.assertEqual(response.status_code, 302)
        # User has access to this page.
        # But the payment method in the order is not "invoicing."
        self.user.is_staff = True
        self.user.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_order_invoice_pdf_generation_with_all_right(self):
        url = reverse('cart:order-invoice-pdf',
                      kwargs={'order_pk': self.order.pk})
        # User has access to this page.
        self.user.is_staff = True
        self.user.save()
        # Set the payment method in the order for "invoicing".
        self.order.payment_method = constants.INVOICING
        self.order.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf;')
