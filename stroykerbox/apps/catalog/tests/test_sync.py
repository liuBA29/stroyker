import json
from unittest.mock import patch

from constance.test import override_config
from model_bakery import baker

from django.core.management import call_command

from .tests_views import CatalogGenericTest


class MockRequest(object):
    def __init__(self, headers, content, status_code):
        self.headers = headers
        self.text = content
        self.status_code = status_code

    def json(self):
        return json.loads(self.text)


def request_get_moy_sklad(*args, **kwargs):
    headers = {'content-type': 'application/json'}
    # https://dev.moysklad.ru/doc/api/remap/1.2/dictionaries/#suschnosti-towar-poluchit-spisok-towarow
    if args[1].endswith('/product/'):
        resp = {'meta': {}, 'rows': [
            {'article': 'test-article-1', 'buyPrice': {'value': 124400},
             'salePrices': [{'value': 212000, 'priceType': {'name': 'Цена продажи'}},
                            {'value': 200000, 'priceType': {'name': 'Цена для друзей'}}]},
            {'article': 'test-article-2', 'buyPrice': {'value': 132400},
             'salePrices': [{'value': 221000, 'priceType': {'name': 'Цена продажи'}},
                            {'value': 205000, 'priceType': {'name': 'Цена для друзей'}}]}
        ]}
    elif args[1].endswith('product-uuid-1'):
        resp = {'meta': {}, 'id': 'product-uuid-1', 'article': 'test-article-1'}
    elif args[1].endswith('product-uuid-2'):
        resp = {'meta': {}, 'id': 'product-uuid-2', 'article': 'test-article-2'}
    else:
        resp = {'meta': {}, 'rows': [
            {
                'meta': {
                    'href': 'https://online.moysklad.ru/api/remap/1.2/entity/product/product-uuid-1?expand=supplier',
                    'uuidHref': 'https://online.moysklad.ru/app/#good/edit?id=product-uuid-1',
                    'metadataHref': 'https://online.moysklad.ru/api/remap/1.2/entity/product/metadata',
                    'type': 'product',
                    'mediaType': 'application/json'
                },
                'stockByStore': [
                {
                    'meta': {
                        'href': 'https://online.moysklad.ru/api/remap/1.2/entity/store/stock-uuid-1',
                        'metadataHref': 'https://online.moysklad.ru/api/remap/1.2/entity/store/metadata',
                        'type': 'store',
                        'mediaType': 'application/json'
                    },
                    'name': 'Не основной склад',
                    'stock': 32,
                    'reserve': 0,
                    'inTransit': 0
                },
                {
                    'meta': {
                        'href': 'https://online.moysklad.ru/api/remap/1.2/entity/store/stock-uuid-2',
                        'metadataHref': 'https://online.moysklad.ru/api/remap/1.2/entity/store/metadata',
                        'type': 'store',
                        'mediaType': 'application/json'
                    },
                    'name': 'Основной склад',
                    'stock': -24,
                    'reserve': 0,
                    'inTransit': 0
                }]
            },
        ]}
    return MockRequest(headers, json.dumps(resp), 200)


@override_config(SYNC_API_URL='https://online.moysklad.ru/api/remap/1.2',
                 SYNC_PRICES_ENABLED=True, SYNC_PRODUCTS_SOURCE='/entity/product/',
                 SYNC_STOCKS_ENABLED=True, SYNC_STOCKS_SOURCE='/report/stock/bystore/?groupBy=product')
class CatalogSyncTest(CatalogGenericTest):
    def setUp(self):
        super().setUp()
        self.product1.sku = 'test-article-1'
        self.product1.save()
        self.product2.sku = 'test-article-2'
        self.product2.save()

    @patch('requests.Session.request', side_effect=request_get_moy_sklad)
    def test_catalog_sync_prices(self, request_products):
        call_command('sync_moy_sklad_prices')
        request_products.assert_called_once()
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.price, 2120)
        self.assertEqual(self.product2.price, 2210)

    @patch('requests.Session.request', side_effect=request_get_moy_sklad)
    def test_catalog_sync_stocks(self, request_stocks):
        baker.make('Stock', third_party_code='stock-uuid-1')
        baker.make('Stock', third_party_code='stock-uuid-2')
        call_command('sync_moy_sklad_stocks')
        request_stocks.assert_called()
        self.product1.refresh_from_db()
        self.assertEqual(list(self.product1.stocks_availability.all().order_by(
            'warehouse__third_party_code').values_list('available', flat=True)), [32])
