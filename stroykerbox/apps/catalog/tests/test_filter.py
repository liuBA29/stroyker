from django.test import TestCase

from model_bakery import baker
from stroykerbox.apps.catalog import models


class FilterFormTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.category = models.Category.objects.create(
            name='Category', slug='category-slug', parent=None)

        # param 1 data
        cls.parameter_checkbox = baker.make('Parameter', name='parameter1',
                                            slug='parameter1', data_type='str', widget='checkbox')
        cls.pv1 = baker.make('ParameterValue', parameter=cls.parameter_checkbox, value_slug='parameter_value_1',
                             value_str='param value 1')
        cls.pv2 = baker.make('ParameterValue', parameter=cls.parameter_checkbox, value_slug='parameter_value_2',
                             value_str='param value 2')

        # param 2 data
        cls.parameter_radio = baker.make('Parameter', name='parameter2',
                                         slug='parameter2', data_type='str', widget='radio')
        cls.pv3 = baker.make('ParameterValue', parameter=cls.parameter_radio, value_slug='parameter_value_3',
                             value_str='param value 3')
        cls.pv4 = baker.make('ParameterValue', parameter=cls.parameter_radio, value_slug='parameter_value_4',
                             value_str='param value 4')

        # param with range widget
        cls.parameter_range = baker.make('Parameter', name='parameter3 range',
                                         slug='parameter3_range', data_type='int', widget='range')
        cls.pv5 = baker.make('ParameterValue', parameter=cls.parameter_range, value_slug='parameter_value_5',
                             value_str='33')

        # category params memb. data
        cls.cpm1 = baker.make('CategoryParameterMembership', category=cls.category, parameter=cls.parameter_checkbox,
                              display=True)
        cls.cpm2 = baker.make('CategoryParameterMembership', category=cls.category, parameter=cls.parameter_radio,
                              display=True)
        cls.cpm3 = baker.make('CategoryParameterMembership', category=cls.category, parameter=cls.parameter_range,
                              display=True)
        # products objects
        cls.product1 = baker.make(
            'Product', category=cls.category, published=True, price=200)
        cls.product2 = baker.make(
            'Product', category=cls.category, published=True, price=300)
        cls.product3 = baker.make(
            'Product', category=cls.category, published=True, price=400)

        # products params data
        cls.ppvm1 = models.ProductParameterValueMembership.objects.create(
            product=cls.product1, parameter=cls.parameter_checkbox)
        cls.ppvm2 = models.ProductParameterValueMembership.objects.create(
            product=cls.product1, parameter=cls.parameter_radio)

        cls.ppvm3 = models.ProductParameterValueMembership.objects.create(
            product=cls.product2, parameter=cls.parameter_radio)

        cls.ppvm4 = models.ProductParameterValueMembership.objects.create(
            product=cls.product3, parameter=cls.parameter_range, value_decimal=44)

        cls.ppvm1.parameter_value.add(cls.pv1)
        cls.ppvm1.parameter_value.add(cls.pv2)
        cls.ppvm2.parameter_value.add(cls.pv2)
        cls.ppvm3.parameter_value.add(cls.pv3)
        cls.ppvm4.parameter_value.add(cls.pv5)

    def test_category_page_with_filter_common(self):
        url = self.category.get_absolute_url()
        # get products with 1 param
        response = self.client.get(
            f'{url}?{self.parameter_checkbox.slug}={self.pv1.value_slug}')
        form = response.context['filter_form']

        self.assertTrue(form.is_valid())
        products = form.get_filtered_products()
        self.assertEqual(products.count(), 1)
        self.assertEqual(products[0].pk, self.product1.pk)

        # get products with 2 param
        response = self.client.get(
            f'{url}?{self.parameter_checkbox.slug}={self.pv1.value_slug}&{self.parameter_checkbox.slug}={self.pv2.value_slug}')  # noqa
        form = response.context['filter_form']

        self.assertTrue(form.is_valid())
        products = form.get_filtered_products()
        self.assertEqual(products.count(), 1)
        self.assertEqual(products[0].pk, self.product1.pk)

        # get products with more params
        response = self.client.get(
            f'{url}?{self.parameter_checkbox.slug}={self.pv1.value_slug}&{self.parameter_radio.slug}={self.pv2.value_slug}&{self.parameter_range.slug}={self.pv5.value_slug}')  # noqa
        form = response.context['filter_form']

        self.assertTrue(form.is_valid())
        products = form.get_filtered_products()
        self.assertEqual(products.count(), 1)
        self.assertEqual(products[0].pk, self.product1.pk)

    def test_filter_param_widget_radio(self):
        url = self.category.get_absolute_url()
        # get products for param 1
        response = self.client.get(
            f'{url}?{self.parameter_radio.slug}={self.pv3.value_slug}')
        form = response.context['filter_form']

        self.assertTrue(form.is_valid())
        products = form.get_filtered_products()
        self.assertEqual(products.count(), 1)
        self.assertEqual(products[0].pk, self.product2.pk)

    def test_filter_param_widget_default(self):
        # param1 widget is default (select)
        self.parameter_checkbox.widget = ''
        self.parameter_checkbox.save()

        url = self.category.get_absolute_url()
        # get products for param 1
        response = self.client.get(
            f'{url}?{self.parameter_checkbox.slug}={self.pv1.value_slug}')
        form = response.context['filter_form']

        self.assertTrue(form.is_valid())
        products = form.get_filtered_products()
        self.assertEqual(products.count(), 1)
        self.assertEqual(products[0].pk, self.product1.pk)

        self.parameter_checkbox.widget = 'checkbox'
        self.parameter_checkbox.save()
