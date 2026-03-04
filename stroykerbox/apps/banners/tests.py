from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command
from django.core import mail

from model_bakery import baker
from constance import config
from stroykerbox.apps.catalog.models import Category
from stroykerbox.apps.banners.tasks import notify_advertisers_banner_expires


class BannerGenericTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        baker.make(Category, lft=None, rght=None, published=True, level=0)

    def setUp(self):
        self.banner = baker.make('Banner', _create_files=True)


class BannerTest(BannerGenericTest):

    def test_ajax_increase_view_counter(self):
        url = reverse('banners:views-increment')
        self.assertEqual(self.banner.views_counter, 0)
        response = self.client.post(url, {'pk': self.banner.pk},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 204)
        self.banner.refresh_from_db()
        self.assertEqual(self.banner.views_counter, 1)

    def test_ajax_increase_click_counter(self):
        url = reverse('banners:clicks-increment')
        self.assertEqual(self.banner.clicks_counter, 0)
        response = self.client.post(url, {'pk': self.banner.pk},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 204)
        self.banner.refresh_from_db()
        self.assertEqual(self.banner.clicks_counter, 1)

    def test_banner_visibility_on_page_without_useful_date(self):
        display_url = baker.make('BannerDisplayUrl', banner=self.banner,
                                 url=reverse('catalog:index'))
        response = self.client.get(display_url.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.banner.name)

    def test_banner_visibility_on_page_with_useful_date(self):
        display_url = baker.make('BannerDisplayUrl', banner=self.banner,
                                 url=reverse('catalog:index'))
        today = date.today()
        self.banner.start_date = today
        self.banner.end_date = today + timedelta(days=5)
        self.banner.save()
        response = self.client.get(display_url.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.banner.name)


class BannerTasksTest(BannerGenericTest):

    def test_expires_nofity_from_command(self):
        today = date.today()
        self.banner.start_date = today
        self.banner.end_date = today + timedelta(days=config.BANNERS_NOTIFY_DAYS_BEFORE_EXPIRE)
        self.banner.advertiser_email = 'someemail.222@slfjdljf.ru'
        self.banner.save()
        self.assertIsNone(self.banner.renewal_notice_date)

        call_command('banner_expires_notify')

        self.banner.refresh_from_db()
        self.assertEqual(self.banner.renewal_notice_date, today)
        self.assertEqual(len(mail.outbox), 1)

    def test_expires_nofity_from_function(self):
        today = date.today()
        self.banner.start_date = today
        self.banner.end_date = today + timedelta(days=config.BANNERS_NOTIFY_DAYS_BEFORE_EXPIRE)
        self.banner.advertiser_email = 'someemail.222@slfjdljf.ru'
        self.banner.save()

        notify_advertisers_banner_expires()

        self.banner.refresh_from_db()
        self.assertEqual(self.banner.renewal_notice_date, today)
        self.assertEqual(len(mail.outbox), 1)
