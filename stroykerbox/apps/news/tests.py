from django.test import TestCase
from django.urls import reverse

from model_bakery import baker

from .models import NEWS_POST_TYPE_NEWS, NEWS_POST_TYPE_PROMO


class NewsTest(TestCase):
    def setUp(self):
        self.news = baker.make('News', published=True,
                               post_type=NEWS_POST_TYPE_NEWS, _quantity=3, _create_files=True)
        self.promos = baker.make('News', published=True,
                                 post_type=NEWS_POST_TYPE_PROMO, _quantity=3, _create_files=True)

    def test_news_list_page(self):
        response = self.client.get(reverse('news:news_list'))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'news/news_list.html')
        for news in self.news:
            self.assertContains(response, news.title)

    def test_promo_list_page(self):
        response = self.client.get(reverse('news:promo_list'))
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'news/promo_list.html')
        for promo in self.promos:
            self.assertContains(response, promo.title)

    def test_news_detail_page(self):
        news = self.news[0]
        response = self.client.get(news.get_absolute_url())
        self.assertEqual(200, response.status_code)
        self.assertContains(response, news.title)
        self.assertTemplateUsed(response, 'news/news_details.html')

    def test_promo_detail_page(self):
        promo = self.promos[0]
        response = self.client.get(promo.get_absolute_url())
        self.assertEqual(200, response.status_code)
        self.assertContains(response, promo.title)
        self.assertTemplateUsed(response, 'news/promo_details.html')

    def test_news_attached_files(self):
        news = self.news[0]
        files = baker.make('NewsFile', news=news, _quantity=3, _create_files=True)
        self.assertEqual(len(news.files.all()), len(files))

    def test_news_attached_images(self):
        news = self.news[0]
        images = baker.make('NewsImage', news=news, _quantity=3, _create_files=True)
        self.assertEqual(len(news.images.all()), len(images))
