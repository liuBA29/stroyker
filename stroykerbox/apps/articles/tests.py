from django.test import TestCase
from django.urls import reverse

from model_bakery import baker


class ArticlesTest(TestCase):
    def setUp(self):
        self.articles = baker.make(
            'Article', body='some body text', published=True, _quantity=3, _create_files=True)

    def test_article_list_page(self):
        url = reverse('articles:article-list')
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertEqual(len(response.context['articles']), len(self.articles))
        for article in self.articles:
            self.assertContains(response, article.title)

    def test_article_detail_page(self):
        article = self.articles[0]
        url = reverse('articles:article-details',
                      kwargs={'slug': article.slug})
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, article.title)

    def test_article_unpublished_detail_page(self):
        article = self.articles[0]
        article.published = False
        article.save()
        url = reverse('articles:article-details',
                      kwargs={'slug': article.slug})
        response = self.client.get(url)
        self.assertEqual(404, response.status_code)
