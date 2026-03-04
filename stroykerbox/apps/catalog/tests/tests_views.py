from django.test import TestCase, override_settings
from django.urls import reverse

from model_bakery import baker
from model_bakery.recipe import Recipe
from stroykerbox.apps.catalog import tasks, models

from . import utils


root_category = Recipe(models.Category, lft=None, rght=None, published=True,
                       level=0, image=utils.create_test_imagefile())
child_category = root_category.extend(level=1)


@override_settings(CACHES={'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache'}})
class CatalogGenericTest(TestCase):
    def setUp(self):
        self.root_category1 = root_category.make()
        self.root_category2 = root_category.make()

        self.child_category1 = child_category.make(parent=self.root_category1)
        self.child_category2 = child_category.make(parent=self.root_category1)

        self.product1 = baker.make('Product', category=self.child_category1,
                                   published=True, price=100)
        self.product2 = baker.make('Product', category=self.child_category1,
                                   published=True, price=150)


class CatalogUrlsTest(CatalogGenericTest):

    def test_url__index(self):
        url = reverse('catalog:index')
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, self.root_category1.name)
        self.assertContains(response, self.root_category2.name)
        self.root_category1.published = False
        self.root_category1.save()
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertNotContains(response, self.root_category1.name)
        self.assertContains(response, self.root_category2.name)

    def test_url__category(self):
        url = reverse('catalog:category',
                      kwargs={'category_slug': self.root_category1.slug})
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'catalog/category-root-page.html')
        self.assertContains(response, self.child_category1.name)
        self.assertContains(response, self.child_category2.name)

    def test_url__category__with_nopublished_categories(self):
        url = reverse('catalog:category',
                      kwargs={'category_slug': self.root_category1.slug})
        self.child_category1.published = False
        self.child_category1.save()
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertNotContains(response, self.child_category1.name)

    def test_url__subcategory(self):
        url = reverse('catalog:subcategory',
                      kwargs={'category_slug': self.root_category1.slug,
                              'subcategory_slug': self.child_category1.slug})
        response = self.client.get(url)

        self.assertEqual(200, response.status_code)

        self.assertTemplateUsed(response, 'catalog/category-child-page.html')
        self.assertTemplateUsed(response, 'catalog/include/product-list.html')

        self.assertContains(response, self.child_category1.name)
        self.assertContains(response, self.product1.name)
        self.assertContains(response, self.product2.name)

    def test_url__product_view(self):
        url = reverse('catalog:product_view', kwargs={
            'category_slug': self.child_category1.slug,
            'product_slug': self.product1.slug
        })
        response = self.client.get(url)

        self.assertEqual(200, response.status_code)
        self.assertContains(response, self.product1.name)

    def test_url__product_view_unpublished_product(self):
        self.product1.published = False
        self.product1.save()
        url = reverse('catalog:product_view', kwargs={
            'category_slug': self.child_category1.slug,
            'product_slug': self.product1.slug
        })
        response = self.client.get(url)

        self.assertEqual(404, response.status_code)

    def test_url__product_search__by_name(self):
        product_title = 'название на русском'
        self.product1.name = product_title
        self.product1.save()
        tasks.search_index_updater(self.product1)

        url = reverse('catalog:product-search')
        url += f'?q={product_title}'
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, self.product1.name)
        self.assertNotContains(response, self.product2.name)

    def test_url__product_search__by_sku(self):
        product_sku = '88333882222'
        self.product1.sku = product_sku
        self.product1.save()
        tasks.search_index_updater(self.product1)

        url = reverse('catalog:product-search')
        url += f'?q={product_sku}'
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, self.product1.name)
        self.assertNotContains(response, self.product2.name)
