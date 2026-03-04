# from django.test import TestCase

# from stroykerbox.apps.catalog import forms

from .tests_views import CatalogGenericTest


class FilterFormTest(CatalogGenericTest):

    def test_filterform_get_filtered_products(self):
        response = self.client.get(self.child_category1.get_absolute_url())
        filter_form = response.context['filter_form']

        self.assertTrue(filter_form.is_valid())
        category_products = self.child_category1.products.all().order_by('name')
        form_products = filter_form.get_filtered_products().order_by('name')
        self.assertEqual(list(category_products), list(form_products))
        self.assertIn(self.product1, form_products)
        self.assertIn(self.product2, form_products)

    def test_filterform_in_catagory_context(self):
        response = self.client.get(self.child_category1.get_absolute_url())
        self.assertEqual(200, response.status_code)
        self.assertIn('filter_form', response.context)

    def test_filterform_contails_price_range_fields(self):
        response = self.client.get(self.child_category1.get_absolute_url())
        filter_form = response.context['filter_form']

        self.assertIn('price_range', filter_form.fields)
        self.assertIn('price_sorting', filter_form.fields)

    def test_filterform_with_price_range_values(self):
        # for self.product1 on page (price 100)
        url = '%s?price_range_0=50&price_range_1=100' % self.child_category1.get_absolute_url()
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, self.product1.name)
        self.assertNotContains(response, self.product2.name)

        # for self.product2 on page (price 150)
        url = '%s?price_range_0=110&price_range_1=200' % self.child_category1.get_absolute_url()
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, self.product2.name)
        self.assertNotContains(response, self.product1.name)

        # range includes all products
        url = '%s?price_range_0=50&price_range_1=200' % self.child_category1.get_absolute_url()
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, self.product1.name)
        self.assertContains(response, self.product2.name)

    def test_filterform_with_price_sorting_value(self):
        asc_sorting_url = '%s?price_sorting=asc' % self.child_category1.get_absolute_url()
        response = self.client.get(asc_sorting_url)
        self.assertEqual(response.context['products'][0], self.product1)

        desc_sorting_url = '%s?price_sorting=desc' % self.child_category1.get_absolute_url()
        response = self.client.get(desc_sorting_url)
        self.assertEqual(response.context['products'][0], self.product2)
