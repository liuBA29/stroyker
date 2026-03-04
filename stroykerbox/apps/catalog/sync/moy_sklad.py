from logging import getLogger
import time

import requests
from requests.auth import HTTPBasicAuth
from django.utils.translation import ugettext as _

from constance import config


logger = getLogger('catalog.moy_sklad.sync')

MOY_SKLAD_STATUSES = {
    # Запрашиваемый ресурс находится по другому URL.
    301: _('Moved Permanently'),
    # Ошибка в структуре JSON передаваемого запроса
    400: _('Request JSON structure error.'),
    # Имя и/или пароль пользователя указаны неверно или заблокированы пользователь или аккаунт
    401: _('Unauthorized'),
    403: _('Forbidden'),  # У вас нет прав на просмотр данного объекта
    404: _('Not Found'),  # Запрошенный ресурс не существует
    # http-метод указан неверно для запрошенного ресурса
    405: _('Method Not Allowed'),
    409: _('Conflict'),  # Указанный объект используется и не может быть удалён
    410: _('Gone'),  # Версия API больше не поддерживается
    # Не указан обязательный параметр строки запроса или поле структуры JSON
    412: _('Precondition Failed'),
    # Размер запроса или количество элементов запроса превышает лимит
    413: _('Request Entity Too Large'),
    # (например, количество позиций передаваемых в массиве positions, превышает 100)
    429: _('Too Many Requests'),  # Превышен лимит количества запросов
    # При обработке запроса возникла непредвиденная ошибка
    500: _('Internal Server Error'),
    502: _('Bad Gateway'),  # Сервис временно недоступен
    503: _('Service Temporarily Unavailable'),  # Сервис временно отключен
    # Превышен таймаут обращения к сервису, повторите попытку позднее
    504: _('Gateway Timeout'),
}


class MoySkladConfig(object):
    def __init__(self, settings):
        for key, value in settings.items():
            setattr(self, key, value)


class RestClient(object):
    def __init__(self, settings):
        self.config = MoySkladConfig(settings)
        self.product = ProductsRequest(self.config)
        self.stock = StocksRequest(self.config)


def get_client():
    auth = {'login': config.SYNC_LOGIN, 'password': config.SYNC_PASSWORD}
    return RestClient(auth)


class MoySkladApiError(Exception):
    pass


class RequestBase(object):
    base_url = config.SYNC_API_URL
    headers = {'Accept-Encoding': 'gzip'}

    def __init__(self, conf):
        self.config = conf
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=15)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        self.auth = HTTPBasicAuth(
            username=self.config.login.encode('utf-8'),
            password=self.config.password.encode('utf-8'),
        )

    def get(self, path):
        full_url = path if 'http' in path else self.base_url + path
        r = self.session.get(full_url, auth=self.auth, headers=self.headers)

        if r.status_code == 200:
            return r.json()

        if r.status_code in MOY_SKLAD_STATUSES:
            msg = MOY_SKLAD_STATUSES[r.status_code]
            if hasattr(r, 'json'):
                msg += f'\n{r.json()}'
            logger.error(msg)
            raise MoySkladApiError({'status': 'error', 'message': msg})

    def get_all_items(self, response, item_key):
        limit_per_batch = config.SYNC_REQUESTS_PER_BATCH
        cnt = 0

        while 'nextHref' in response['meta']:
            for item in response[item_key]:
                yield item

            response = self.get(response['meta']['nextHref'])

        # The limit on the number of requests has been exceeded
        # limit for MySkad apy: 45 req. in 3 sec
        # (https://dev.moysklad.ru/doc/api/remap/1.2/#mojsklad-json-api-obschie-swedeniq-ogranicheniq)
        for item in response[item_key]:
            if cnt > limit_per_batch:
                time.sleep(3)
                cnt = 0
            yield item
            cnt += 1


class ProductsRequest(RequestBase):

    def get_products(self):
        response = self.get(config.SYNC_PRODUCTS_SOURCE)
        return self.get_all_items(response, 'rows')

    def get_product(self, product_id: str):
        url = f'{config.SYNC_PRODUCTS_SOURCE}{product_id}'
        return self.get(url)


class StocksRequest(RequestBase):

    def get_stocks_by_store(self):
        response = self.get(config.SYNC_STOCKS_SOURCE)
        return self.get_all_items(response, 'rows')
