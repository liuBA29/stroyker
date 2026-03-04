from unittest import mock

from django.test import TestCase

from model_bakery import baker
from stroykerbox.apps.commerce import cart
from stroykerbox.apps.users import models


class UserGenericTest(TestCase):
    """ Create user login """

    def setUp(self):
        self.user = models.User.objects.create_user(email='test_user@testmail.com',
                                                    password='test', phone='12345678912')
        self.product = baker.make('Product')
        self.client.force_login(self.user)


@mock.patch('stroykerbox.apps.catalog.models.Product.is_available', return_value=True)
class UserDiscountTest(UserGenericTest):
    def setUp(self):
        super().setUp()
        self.product.price = 222
        self.product.purchase_price = 111
        self.product.save()
        self.user_cart = cart.Cart(self.user)
        self.personal_discount = 20
        self.group_discount = 80
        self.user_discount_group = models.UserDiscountGroup.objects.create(
            name='test group',
            discount=self.group_discount
        )
        self.product_personal_discount_price = (
            (self.product.purchase_price / 100) * self.personal_discount + self.product.purchase_price)
        self.product_group_discount_price = (
            (self.product.purchase_price / 100) * self.group_discount + self.product.purchase_price)

    def test_cart_create(self, _):
        """
        Testing create Cart.
        """
        self.assertIsInstance(self.user_cart, cart.Cart)

    def test_user_without_discount_in_catalog(self, _):
        self.assertEqual(self.product.personal_price(
            self.user), self.product.price)

    def test_user_without_discount_in_cart(self, _):
        self.user_cart.add_product(self.product)
        self.assertEqual(self.user_cart.total_price, self.product.price)

    def test_user_with_personal_discount_in_catalog(self, _):
        self.user.personal_discount = self.personal_discount
        self.user.save()
        self.assertTrue(self.product.personal_price(
            self.user) < self.product.price)
        self.assertTrue(self.product.personal_price(
            self.user) > self.product.purchase_price)
        self.assertEqual(self.product.personal_price(
            self.user), self.product_personal_discount_price)

    def test_user_with_personal_discount_in_cart(self, _):
        self.user.personal_discount = self.personal_discount
        self.user.save()
        self.user_cart.add_product(self.product)
        self.assertTrue(self.user_cart.total_price < self.product.price)
        self.assertTrue(self.user_cart.total_price >
                        self.product.purchase_price)
        self.assertEqual(self.product.personal_price(
            self.user), self.product_personal_discount_price)

    def test_user_with_group_discount_in_catalog(self, _):
        self.user.discount_group = self.user_discount_group
        self.user.save()
        self.assertTrue(self.product.personal_price(
            self.user) < self.product.price)
        self.assertTrue(self.product.personal_price(
            self.user) > self.product.purchase_price)
        self.assertEqual(self.product.personal_price(
            self.user), self.product_group_discount_price)

    def test_user_with_group_discount_in_cart(self, _):
        self.user.discount_group = self.user_discount_group
        self.user.save()
        self.user_cart.add_product(self.product)
        self.assertTrue(self.user_cart.total_price < self.product.price)
        self.assertTrue(self.user_cart.total_price >
                        self.product.purchase_price)
        self.assertEqual(self.product.personal_price(
            self.user), self.product_group_discount_price)

    def test_user_personal_and_group_discount_priority_catalog(self, _):
        self.user.personal_discount = self.personal_discount
        self.user.discount_group = self.user_discount_group
        self.user.save()
        self.assertEqual(self.product.personal_price(
            self.user), self.product_personal_discount_price)

    def test_user_personal_and_group_discount_priority_cart(self, _):
        self.user.personal_discount = self.personal_discount
        self.user.discount_group = self.user_discount_group
        self.user.save()
        self.assertEqual(self.product.personal_price(
            self.user), self.product_personal_discount_price)
