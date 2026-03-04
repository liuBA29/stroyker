from unittest import mock

from django.test import RequestFactory, TestCase
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model

from model_bakery import baker
from django_geoip.middleware import LocationMiddleware
from stroykerbox.apps.catalog.templatetags import catalog_tags
from stroykerbox.apps.catalog.models import NOT_AVAILABLE


class CatalogTemplateTagTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.product = baker.make('Product', published=True, price=100)
        cls.user = get_user_model().objects.create_user(email='test_user@testmail.com',
                                                        password='test', phone='12345678912')

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        middleware = LocationMiddleware()
        middleware.process_request(self.request)

    def test_url_all_qs_tag(self):
        param_field = 'test_param'
        param_field_value = 'test_param_value'
        context = {'request': self.request}
        result = catalog_tags.url_add_qs(
            context, param_field, param_field_value)
        test_url_params = f'{param_field}={param_field_value}'
        self.assertEqual(result, test_url_params)

        new_request = self.factory.get(f'/?{test_url_params}')
        param_field = 'test_param_2'
        param_field_value = 'test_param_value_2'
        context = {'request': new_request}
        result = catalog_tags.url_add_qs(
            context, param_field, param_field_value)
        self.assertEqual(
            result, f'{test_url_params}&{param_field}={param_field_value}')

    def test_render_product_availability_status_tag_product_available(self):
        test_count = 5
        context = {'product': self.product, 'request': self.request}
        # with authorized user
        context['user'] = self.user
        with mock.patch('stroykerbox.apps.catalog.models.Product.available_items_count') as available_count:
            available_count.return_value = test_count
            result = catalog_tags.render_product_availability_status(context)
        self.assertEqual(test_count, result['status'])
        self.assertEqual(None, result['appearance_date'])
        # with anonymous user
        context['user'] = AnonymousUser()
        with mock.patch('stroykerbox.apps.catalog.models.Product.available_items_count') as available_count:
            available_count.return_value = test_count
            result = catalog_tags.render_product_availability_status(context)
            status_name = self.product.get_availability_status_name()
        self.assertEqual(status_name, result['status'])
        self.assertEqual(None, result['appearance_date'])

    def test_render_product_availability_status_tag_product_not_available(self):
        test_count = 0
        context = {'product': self.product, 'request': self.request}
        context['user'] = None
        with mock.patch('stroykerbox.apps.catalog.models.Product.available_items_count') as available_count:
            available_count.return_value = test_count
            result = catalog_tags.render_product_availability_status(context)
        self.assertEqual(NOT_AVAILABLE, result['status'])
