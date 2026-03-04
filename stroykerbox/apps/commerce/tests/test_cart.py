from unittest import mock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from model_bakery import baker
from stroykerbox.apps.catalog.tests import utils
from stroykerbox.apps.commerce import cart


class CartGenericTest(TestCase):
    def setUp(self):
        self.root_category1 = baker.make('Category', level=0, published=True,
                                         lft=None, rght=None)
        self.root_category2 = baker.make('Category', level=0, published=True,
                                         lft=None, rght=None)

        self.child_category1 = baker.make('Category',
                                          parent=self.root_category1, published=True,
                                          level=1, image=utils.create_test_imagefile(),
                                          lft=None, rght=None)
        self.child_category2 = baker.make('Category',
                                          parent=self.root_category1, published=True,
                                          level=1, image=utils.create_test_imagefile(),
                                          lft=None, rght=None)
        self.product1 = baker.make('Product', category=self.child_category1,
                                   published=True, price=100)
        self.product2 = baker.make('Product', category=self.child_category1,
                                   published=True, price=150)
        self.product3 = baker.make('Product', category=self.child_category1,
                                   published=True, price=170)
        self.user = get_user_model().objects.create_user(email='test_user@testmail.com',
                                                         password='test', phone='12345678912')
        self.user_cart = cart.Cart(self.user)


class CommonCartTest(CartGenericTest):
    def test_cart_create(self):
        """
        Testing create Cart.
        """
        self.assertIsInstance(self.user_cart, cart.Cart)

    def test_main_cart_url_by_get(self):
        self.client.force_login(self.user)
        self.session = self.client.session
        self.session['cart'] = self.user_cart
        self.session.save()

        response = self.client.get(reverse('cart:cart'))
        response_cart = response.client.session['cart']
        self.assertIsInstance(response_cart, cart.Cart)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'cart/cart-page.html')

    def test_main_cart_url_by_post(self):
        response = self.client.post(reverse('cart:cart'))
        self.assertEqual(200, response.status_code)
        cart = response.client.session['cart']
        self.assertIsInstance(cart, dict)
        self.assertEqual(200, response.status_code)
        self.assertTrue('products' in cart)
        self.assertTrue('order_pk' in cart)
        self.assertIsNone(cart['order_pk'])


class AddProductCartTest(CartGenericTest):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.session = self.client.session
        self.session['cart'] = self.user_cart
        self.session.save()

    @mock.patch('stroykerbox.apps.catalog.models.Product.is_available', return_value=True)
    def test_cart_method_add_available_product(self, _):
        """
        Add to products product whose available True.
        """
        self.user_cart.add_product(self.product1)
        self.assertEqual(len(self.user_cart.products), 1)

        self.user_cart.add_product(self.product2)
        self.assertEqual(len(self.user_cart.products), 2)

    @mock.patch('stroykerbox.apps.catalog.models.Product.is_available', return_value=True)
    def test_url_add_available_product(self, _):
        response = self.client.get(reverse('cart:add_to_cart', kwargs={
            'product_pk': self.product1.pk}))
        self.assertContains(response, 'success')
        self.assertNotContains(response, 'error')
        self.assertEqual(len(self.client.session['cart']['products']), 1)

        response = self.client.get(reverse('cart:add_to_cart', kwargs={
            'product_pk': self.product2.pk}))
        self.assertContains(response, 'success')
        self.assertNotContains(response, 'error')
        self.assertEqual(len(self.client.session['cart']['products']), 2)

    def test_cart_method_add_not_available_product(self):
        """
        Add to products product whose available False.
        """
        self.assertRaises(cart.ItemUnavailable,
                          self.user_cart.add_product, self.product3)

    def test_url_add_not_available_product(self):
        url = reverse('cart:add_to_cart', kwargs={
                      'product_pk': self.product3.pk})

        response = self.client.get(url)
        self.assertNotContains(response, 'success')
        self.assertContains(response, 'error')
        self.assertEqual(
            len(getattr(self.client.session['cart'], 'products')), 0)

    @mock.patch('stroykerbox.apps.catalog.models.Product.is_available', return_value=True)
    def test_cart_method_add_products_already_in(self, _):
        """
        If product in cart funcion get ItemAlreadyAdded exeption.
        """
        self.user_cart.add_product(self.product1)
        self.user_cart.add_product(self.product2)
        self.assertRaises(cart.ItemAlreadyAdded,
                          self.user_cart.add_product, self.product1)
        self.assertRaises(cart.ItemAlreadyAdded,
                          self.user_cart.add_product, self.product2)

    @mock.patch('stroykerbox.apps.catalog.models.Product.is_available', return_value=True)
    def test_url_add_products_already_in(self, _):
        """
        By url.
        """
        url = reverse('cart:add_to_cart', kwargs={
                      'product_pk': self.product1.pk})
        response = self.client.get(url)
        self.assertContains(response, 'success')

        response = self.client.get(url)
        self.assertContains(response, 'error')
        self.assertEqual(len(self.client.session['cart']['products']), 1)

    @mock.patch('stroykerbox.apps.catalog.models.Product.is_available', return_value=True)
    def test_cart_method_add_product_quantity(self, _):
        """
        Add to products product whose quantity is 2
        """
        self.user_cart.add_product(self.product1)
        self.user_cart.add_product(self.product2, 3)
        self.user_cart.add_product(self.product3, quantity=2)

        self.assertEqual(len(self.user_cart.products), 3)
        self.assertEqual(self.user_cart.products[self.product1.pk], 1)
        self.assertEqual(self.user_cart.products[self.product2.pk], 3)
        self.assertEqual(self.user_cart.products[self.product3.pk], 2)


@mock.patch('stroykerbox.apps.catalog.models.Product.is_available', return_value=True)
class RemoveFromCartTest(CartGenericTest):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.session = self.client.session
        self.session['cart'] = self.user_cart
        self.session.save()

    def test_cart_method_remove_products(self, _):
        # add products
        self.user_cart.add_product(self.product1)
        self.user_cart.add_product(self.product2)
        self.assertEqual(len(self.user_cart.products), 2)

        self.user_cart.remove_product(self.product1)
        self.assertEqual(len(self.user_cart.products), 1)
        self.assertIsNot(self.product1.pk, self.user_cart.products)

        self.user_cart.remove_product(self.product2)
        self.assertEqual(len(self.user_cart.products), 0)
        self.assertIsNot(self.product2.pk, self.user_cart.products)

    def test_url_remove_products(self, _):
        """
        By url.
        """
        # add products
        add_url = reverse('cart:add_to_cart', kwargs={
            'product_pk': self.product1.pk})
        response = self.client.get(add_url)
        self.assertContains(response, 'success')
        self.assertEqual(len(self.client.session['cart']['products']), 1)

        remove_url = reverse('cart:remove_from_cart', kwargs={
            'product_pk': self.product1.pk})
        self.client.get(remove_url)
        self.assertEqual(len(self.client.session['cart']['products']), 0)

    def test_cart_method_remove_product_not_found(self, _):
        """
        Get exception ProductNotFound if remove product
        is not in products.
        """
        self.assertEqual(len(self.user_cart.products), 0)
        self.assertRaises(cart.ProductNotFound,
                          self.user_cart.remove_product, self.product1)

    def test_url_remove_product_not_found(self, _):
        """
        By url.
        """
        remove_url = reverse('cart:remove_from_cart', kwargs={
            'product_pk': self.product1.pk})
        response = self.client.get(remove_url)
        # self.assertEqual(
        #     len(self.client.session['cart']['products']), 0)
        self.assertEqual(400, response.status_code)
        self.assertEqual(
            len(getattr(self.client.session['cart'], 'products')), 0)


@mock.patch('stroykerbox.apps.catalog.models.Product.is_available', return_value=True)
@mock.patch('stroykerbox.apps.catalog.models.Product.available_items_count', return_value=100)
class UpdateQuantityCartTest(CartGenericTest):
    """
    Testing funcion update_quantity.
    """

    @mock.patch('stroykerbox.apps.catalog.models.Product.is_available', return_value=True)
    @mock.patch('stroykerbox.apps.catalog.models.Product.available_items_count', return_value=100)
    def setUp(self, _, __):
        super().setUp()
        self.func = self.user_cart.update_quantity
        # add products
        self.user_cart.add_product(self.product1)
        self.user_cart.add_product(self.product2)
        self.user_cart.add_product(self.product3)

    def test_update_quantity_int(self, _, __):
        self.func(self.product1, 4)
        self.assertEqual(self.user_cart.products[self.product1.pk], 4)

    def test_update_quantity_float(self, _, __):
        self.func(self.product1, 2.3)
        self.assertEqual(self.user_cart.products[self.product1.pk], 2)

    def test_update_quantity_str(self, _, __):
        self.func(self.product1, '3')
        self.assertEqual(self.user_cart.products[self.product1.pk], 3)

    def test_not_update_quantity_str(self, _, __):
        """ Not update if ValueError or TypeError """
        self.assertRaises(cart.WrongQuantity, self.func, self.product1, 'abc')

    def test_not_update_quantity_tuple_(self, _, __):
        """ Not update if ValueError or TypeError """
        self.assertRaises(cart.WrongQuantity, self.func, self.product1, (1, 4))

    def test_not_update_quantity_dict(self, _, __):
        """ Not update if ValueError or TypeError """
        self.assertRaises(cart.WrongQuantity, self.func,
                          self.product1, {'a': 1})

    def test_not_update_quantity_list(self, _, __):
        """ Not update if ValueError or TypeError """
        self.assertRaises(cart.WrongQuantity, self.func, self.product1, [1])

    def test_not_update_quantity_set(self, _, __):
        """ Not update if ValueError or TypeError """
        self.assertRaises(cart.WrongQuantity, self.func, self.product1, {1})

    def test_not_update_quantity_eq(self, _, __):
        """ Not update if quantity <= 0 """
        self.assertRaises(cart.WrongQuantity, self.func, self.product1, 0.5)
        self.assertRaises(cart.WrongQuantity, self.func, self.product1, '0')
        self.assertRaises(cart.WrongQuantity, self.func, self.product1, -3)

    def test_not_update_quantity_gt_available(self, _, __):
        """
        Not update if quantity > available_items_count.
        """
        # Maximum available in shop is 100
        self.assertRaises(cart.WrongQuantity, self.func, self.product1, 105)

    def test_update_quantity_up(self, _, __):
        url = reverse('cart:update_product_quantity',
                      kwargs={'product_pk': self.product1.pk})
        up_response = self.client.get('%s?q=up' % url)
        self.assertEqual(up_response.json()['quantity'], 1)
        self.assertContains(up_response, 'success')

    def test_update_quantity_down(self, _, __):
        url = reverse('cart:update_product_quantity',
                      kwargs={'product_pk': self.product1.pk})
        down_response = self.client.get('%s?q=down' % url)
        self.assertEqual(down_response.json()['quantity'], -1)
        self.assertContains(down_response, 'error')

    def test_update_quantity_with_wrong_get(self, _, __):
        url = reverse('cart:update_product_quantity',
                      kwargs={'product_pk': self.product1.pk})
        wrong_response = self.client.get('%s?q=somewrongword' % url)
        self.assertEqual(wrong_response.json()['quantity'], 0)
        self.assertContains(wrong_response, 'error')

    def test_total_price_is_updated(self, _, __):
        total_price = self.user_cart.total_price
        self.user_cart.update_quantity(self.product1, 2)
        self.assertGreater(self.user_cart.total_price, total_price)
