from unittest import mock

from django.template import Context, Template
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth.forms import AuthenticationForm

from model_bakery import baker
from stroykerbox.apps.commerce import cart, forms
from stroykerbox.apps.commerce.templatetags import commerce_tags


class CommerceTemplateTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        pass

    def setUp(self):
        self.factory = RequestFactory()
        self.user = get_user_model().objects.create_user(email='test_user@testmail.com',
                                                         password='test', phone='12345678912')

    def create_user_cart(self, products=True):
        self.user_cart = cart.Cart(self.user)
        self.session = self.client.session
        if products:
            product = baker.make('Product', published=True, price=120)
            with mock.patch('stroykerbox.apps.catalog.models.Product.is_available',
                            return_value=True):
                self.user_cart.add_product(product)
            self.user_cart.save_to_session(self.session)
        self.session.save()
        self.client.force_login(self.user)

    @mock.patch('stroykerbox.apps.catalog.models.Product.is_available',
                return_value=True)
    def test_render_cart_tag(self, _):
        self.create_user_cart()

        request = self.factory.get('/')
        request.session = self.client.session
        request.user = self.user

        out = Template(
            "{% load commerce_tags %}"
            "{% render_cart %}"
        ).render(Context({'request': request}))

        self.assertIn('<a class="cart-count" href="/cart/">1 товар</a>', out)

    @mock.patch('stroykerbox.apps.catalog.models.Product.is_available',
                return_value=True)
    def test_render_cart_tag_context(self, _):
        self.create_user_cart()

        request = self.factory.get('/')
        request.session = self.client.session
        request.user = self.user
        context = {'request': request}
        result_context = commerce_tags.render_cart(context)
        self.assertIsInstance(result_context['cart'], cart.Cart)

    def test_render_login_form_tag_not_authorized(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        out = Template(
            "{% load commerce_tags %}"
            "{% render_commerce_login_form %}"
        ).render(Context({'request': request}))
        self.assertIn(
            '<form method="post" action="/account/login/" class="form">', out)

    def test_render_login_form_tag_authorized(self):
        request = self.factory.get('/')
        request.user = self.user
        out = Template(
            "{% load commerce_tags %}"
            "{% render_commerce_login_form %}"
        ).render(Context({'request': request}))
        self.assertEqual(
            out, '\n\n\n<p>Вы уже авторизированы на сайте</p>\n\n')

    def test_render_login_form_tag_context(self):
        request = self.factory.get('/')
        context = {'request': request}
        result_context = commerce_tags.render_commerce_login_form(context)
        self.assertIsInstance(result_context['form'], AuthenticationForm)
        self.assertEqual(result_context['next'], request.path)

    def test_get_ajax_cost_url_tag_for_pickup_delivery_form(self):
        delivery_forms = (forms.PickUpDeliveryForm, forms.ToAddressDeliveryForm,
                          forms.ToTCDeliveryForm)
        for form in delivery_forms:
            delivery_form = form()
            model = delivery_form._meta.model
            self.assertTrue(hasattr(model, 'get_cost_url') and callable(
                getattr(model, 'get_cost_url')))
            uri = delivery_form._meta.model.get_cost_url() or ''
            out = Template(
                "{% load commerce_tags %}"
                "{% get_ajax_cost_url delivery_form %}"
            ).render(Context({'delivery_form': delivery_form}))
            self.assertEqual(out, uri)
