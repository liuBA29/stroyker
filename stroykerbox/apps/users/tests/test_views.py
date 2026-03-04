import datetime

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core import mail
from django.conf import settings

from model_bakery import baker
from constance.test import override_config
from stroykerbox.apps.users.forms import RegistrationForm


class UsersViewsTest(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(email='test_user@testmail.com',
                                                         password='test', phone='12345678912')

    def test_login_view(self):
        url = reverse('login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.resolver_match._func_path,
                         'stroykerbox.apps.users.views.UsersLoginView')

    def test_login_view_as_post_with_remeber_me(self):
        url = reverse('login')
        # without passing "remember_me"
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.client.session.get_expire_at_browser_close())
        # with "remember_me"
        response = self.client.post(url, {'remember_me': True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.client.session.get_expire_at_browser_close())

    def test_profile_view_with_get_method(self):
        url = reverse('users:profile')
        # as anonymous
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        # as logged in
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/profile.html')

    def test_profile_view_with_post_method(self):
        url = reverse('users:profile')
        self.client.force_login(self.user)
        response = self.client.post(url)
        form = response.context['form']
        # required fields are not filled
        self.assertFalse(form.is_valid())

        response = self.client.post(url, {
            'company': 'some company',
            'name': 'user name',
            'phone': '28937293729'})
        self.assertIsNone(response.context)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('users:profile_saved'))

    def test_registration_view_with_get_method(self):
        url = reverse('registration')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.resolver_match._func_path,
                         'stroykerbox.apps.users.views.registration')
        self.assertIsInstance(response.context['form'], RegistrationForm)
        self.assertTemplateUsed(response, 'registration/registration.html')

    @override_config(MANAGER_EMAILS='manager1@mail.localhost, manager2@mail.localhost')
    def test_registration_view_with_post_method(self):
        url = reverse('registration')
        response = self.client.post(url, {
            'email': 'some_test_email@loclalhost.local',
            'name': 'person name',
            'phone': '72338882233',
            'company': 'company name',
            'password1': 'userpassword',
            'password2': 'userpassword',
            'i_agree': True
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('registration_success'))
        # new registration notification sent to manager
        self.assertEqual(len(mail.outbox), 1)

    def test_registration_activate(self):
        url = reverse('registration_activate')
        token = PasswordResetTokenGenerator().make_token(self.user)
        response = self.client.get(url, {'email': self.user.email,
                                         'token': token})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, settings.LOGIN_REDIRECT_URL)
        # token is wrong
        response = self.client.get(url, {'email': self.user.email,
                                         'token': 'some_wrong_token'})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'registration/registration_activate.html')

    def test_order_list_view(self):
        order_total_price = 2383
        completed_orders = baker.make('Order',
                                      _quantity=2, user=self.user,
                                      status='completed', total_price=order_total_price)
        new_orders = baker.make('Order',
                                _quantity=2, user=self.user, status='new')
        self.client.force_login(self.user)
        response = self.client.get(reverse('users:orders_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(completed_orders) + len(new_orders),
                         response.context['orders'].count())
        self.assertEqual(order_total_price * len(completed_orders),
                         int(response.context['orders_sum']['total_price__sum']))
        self.assertTemplateUsed(response, 'users/orders_list.html')

    def test_order_details_view(self):
        self.client.force_login(self.user)
        delivery_object = baker.make('PickUpDelivery')
        order = baker.make('Order', user=self.user, delivery=delivery_object)
        url = reverse('users:order_details', kwargs={'order_pk': order.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'users/order_details.html')

    def test_document_list_view(self):
        self.client.force_login(self.user)
        user_docs = baker.make('UserDocument',
                               _quantity=2, _create_files=True, user=self.user)
        response = self.client.get(reverse('users:docs_index_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['docs'].count(), len(user_docs))
        self.assertTemplateUsed(response, 'users/userdocs-list.html')

    def test_document_list_view_by_year(self):
        self.client.force_login(self.user)
        baker.make('UserDocument',
                   _quantity=2, _create_files=True, user=self.user,
                   doc_date=datetime.date(2000, 2, 1))
        user_docs_2003 = baker.make('UserDocument',
                                    _quantity=3, _create_files=True, user=self.user,
                                    doc_date=datetime.date(2003, 2, 1))
        response = self.client.get(reverse('users:docs_year_list',
                                           kwargs={'year': 2003}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['docs'].count(), len(user_docs_2003))

    def test_document_list_view_by_month(self):
        self.client.force_login(self.user)
        baker.make('UserDocument',
                   _quantity=2, _create_files=True, user=self.user,
                   doc_date=datetime.date(2000, 2, 1))
        baker.make('UserDocument',
                   _quantity=3, _create_files=True, user=self.user,
                   doc_date=datetime.date(2003, 2, 1))

        with_testing_monts_5 = baker.make('UserDocument',
                                          _quantity=3, _create_files=True, user=self.user,
                                          doc_date=datetime.date(2003, 5, 1))

        response = self.client.get(reverse('users:docs_month_list',
                                           kwargs={'year': 2003, 'month': 5}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['docs'].count(), len(with_testing_monts_5))
