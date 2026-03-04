from django.core.cache import cache
from django.urls import reverse
from django.test import TestCase
from django.contrib.sites.models import Site

from model_bakery import baker
from model_bakery.recipe import Recipe

from .models import RobotsTxt
from .views import ROBOT_TXT_CACHE_KEY_PREFIX


class SeoGenericTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.site = Site.objects.get_current()


class SeoTest(SeoGenericTest):
    def setUp(self):
        self.robots_txt = RobotsTxt.objects.create(site=self.site,
                                                   content='some robots.txt file content')

    def test_robots_txt(self):
        response = self.client.get(reverse('robots_txt'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, bytes(
            self.robots_txt.content, 'utf8'))
        self.assertEqual(response._headers['content-type'][1], 'text/plain')

    def test_robots_txt_cache(self):
        cached = cache.get(f'{ROBOT_TXT_CACHE_KEY_PREFIX}:{self.robots_txt.pk}')
        self.assertTrue(cached)

        new_content = 'some new content'
        self.robots_txt.content = new_content
        self.robots_txt.save()
        new_cached = cache.get(f'{ROBOT_TXT_CACHE_KEY_PREFIX}:{self.robots_txt.pk}')
        self.assertEqual(new_cached, new_content)


class SitemapTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = reverse('django.contrib.sitemaps.views.sitemap')
        cls.news = baker.make('News')
        cls.article = baker.make('Article', body='some text')
        cls.staticpage = baker.make('staticpages.Page', published=True)

        root_category = Recipe('Category', lft=None, rght=None, published=True,
                               level=0, _create_files=True)
        child_category = root_category.extend(level=1)
        parent_category = root_category.make()
        cls.catalog_category = child_category.make(parent=parent_category)
        cls.catalog_product = baker.make('Product', category=cls.catalog_category, published=True)

    def setUp(self):
        cache.clear()

    def test_news_sitemap(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.news.get_absolute_url())

    def test_article_sitemap(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.article.get_absolute_url())

    def test_category_sitemap(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.catalog_category.get_absolute_url())

    def test_product_sitemap(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.catalog_product.get_absolute_url())

    def test_staticpage_sitemap(self):
        response = self.client.get(self.url)
        self.assertContains(response, self.staticpage.get_absolute_url())
