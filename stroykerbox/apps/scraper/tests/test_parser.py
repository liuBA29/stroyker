from io import BytesIO
from os import path
from PIL import Image
from pyquery import PyQuery as Pq
from django.test import TestCase
from django.conf import settings
from django.core.management import call_command

from unittest.mock import patch
from model_bakery import baker


def create_image(size=(100, 100), image_mode='RGB', image_format='JPEG'):
    data = BytesIO()
    Image.new(image_mode, size).save(data, image_format)
    data.seek(0)
    return data


class MockRequest(object):
    def __init__(self, headers, content, status_code):
        self.headers = headers
        self.content = content
        self.text = content
        self.data = content
        self.status_code = status_code
        self.status = status_code


def request_get_image_side_effect(*args, **kwargs):
    headers = {'content-type': 'image/jpeg'}
    image = create_image()
    return MockRequest(headers, image.getvalue(), 200)


def request_get_dom_side_effect(*args, **kwargs):
    headers = {'content-type': 'text/html'}
    html_path = path.join(settings.BASE_DIR, 'apps', 'scraper', 'tests', 'html', 'category.html')
    with open(html_path, 'r') as f:
        return MockRequest(headers, f.read(), 200)


def request_get_product_dom_side_effect(*args, **kwargs):
    html_path = path.join(settings.BASE_DIR, 'apps', 'scraper', 'tests', 'html', 'product.html')
    with open(html_path, 'r') as f:
        return Pq(f.read())


class TestCategoryParser(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.category = baker.make('catalog.Category', name='test-category', slug='test-category')
        city = baker.make('django_geoip.City', name='test-city')
        location = baker.make('locations.Location', name='test-location', city=city)
        cls.partner = baker.make('addresses.Partner', name='test-partner', slug='test-partner', phone='79001234567',
                                 email='test@partner.com', address='test-address',
                                 geo_latitude=53.195873, geo_longitude=50.100193, location=location)
        cls.scraper = baker.make(
            'scraper.Scraper',
            partner=cls.partner,
            category=cls.category,
            category_source_url='https://samara.kuvalda.ru/catalog/2023/',
            filter_option_selector='catalog-filter',
            filter_json_attr='json-data',
            filter_option_title_selector='.filter-option__title',
            filter_option_checkbox_selector='.filter-checkbox__link, .filter-checkbox__label',
            filter_option_range_selector='.filter-range',
            pagination_selector='.pagination__item',
            page_prefix='page-',
            product_url_selector='.catalog__list-item .link',
            product_code_selector='.product-header__code-title',
            product_price_selector='.product-buy__price-value span',
            product_name_selector='.page-header__title',
            product_description_selector='.product-specs__descr',
            product_inline_params_selector='.product-specs__table',
            product_inline_params_map='{"Мощность двигателя": ["л.с."], "Ширина захвата": ["см"], '
                                      '"Высота захвата": ["см"], '
                                      '"Дальность выброса снега": ["от", "до", "м", "мм", "см"]}',
            product_image_selector='.product-gallery__slider-image',
            product_image_src_attr='data-src',
            product_old_images_delete=True,
            product_uom_name='шт',
            product_published=False,
        )

    @patch('requests.get', side_effect=request_get_dom_side_effect)
    @patch('stroykerbox.apps.scraper.parser.CategoryParser.get_product_dom',
           side_effect=request_get_product_dom_side_effect)
    @patch('urllib3.PoolManager.request', side_effect=request_get_image_side_effect)
    def test_category_parser(self, request_get_dom, request_get_product_dom, request_get_image):
        call_command('parse_category_products', self.partner.slug, self.category.slug)
