from logging import getLogger

from django.utils.functional import cached_property
from django.conf import settings
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.utils.translation import ugettext_lazy as _
from constance import config
import requests

from .models import VKProductMembership
from .conf import UNLOAD_VARIANT_CHECKED, UNLOAD_VARIANT_OFF

logger = getLogger(__name__)


def vk_settings_check():
    msg = []
    if config.VK_MARKET_UNLOAD_VARIANT == UNLOAD_VARIANT_OFF:
        msg.append(
            _('Выгрузка товаров на площадку VK отключена (настройка VK_MARKET_UNLOAD_VARIANT )'))
    if not config.VK_MARKET_OWNER_ID:
        msg.append(
            _('Не указан идентификатор владельца товара в VK '
              '(группы-сообщества) (настройка VK_MARKET_OWNER_ID )'))
    if not config.VK_MARKET_APP_ID:
        msg.append(
            _('Не указан ID приложения в VK (настройка VK_MARKET_APP_ID )'))
    if not config.VK_MARKET_SECRET_KEY:
        msg.append(
            _('Не указан секретный ключ (настройка VK_MARKET_SECRET_KEY )'))
    if not config.VK_MARKET_SERVICE_KEY:
        msg.append(
            _('Не указан сервисный ключ (настройка VK_MARKET_SERVICE_KEY )'))
    if not config.VK_MARKET_API_VERSION:
        msg.append(
            _('Не указана версия API (настройка VK_MARKET_API_VERSION)'))
    if not config.VK_MARKET_ACCESS_TOKEN:
        msg.append(
            _('Не получен токен доступа (настройка VK_MARKET_ACCESS_TOKEN)'))

    return msg


def vk_market_enabled():
    return all((
        config.VK_MARKET_UNLOAD_VARIANT != UNLOAD_VARIANT_OFF,
        config.VK_MARKET_OWNER_ID,
        config.VK_MARKET_APP_ID,
        config.VK_MARKET_SECRET_KEY,
        config.VK_MARKET_SERVICE_KEY,
        config.VK_MARKET_API_VERSION,
        config.VK_MARKET_ACCESS_TOKEN
    ))


class VKMarket:
    # vk не дает загружать более 4-х пикчей для товара.
    VK_MARKET_IMG_LIMIT = 4

    VK_API_MAIN_URI = 'https://api.vk.com/method'

    # def __new__(cls):
    #     if not hasattr(cls, 'instance'):
    #         cls.instance = super().__new__(cls)
    #     return cls.instance

    def __init__(self):
        self.client_id = config.VK_MARKET_APP_ID
        self.group_id = abs(config.VK_MARKET_OWNER_ID)

    @cached_property
    def common_params(self):
        return {
            'group_id': self.group_id,
            'owner_id': config.VK_MARKET_OWNER_ID,
            'v': config.VK_MARKET_API_VERSION,
        }

    def get_vk_categories(self, count=1000):
        uri = f'{self.VK_API_MAIN_URI}/market.getCategories'
        params = self.common_params
        params['count'] = count
        resp = requests.get(uri, params=params, headers=self.headers)
        try:
            return resp.json()
        except Exception as e:
            logger.exception(e)
        return {}

    @cached_property
    def headers(self):
        return {
            'Authorization': f'Bearer {config.VK_MARKET_ACCESS_TOKEN}'
        }

    def get_upload_url(self):
        uri = 'https://api.vk.com/method/photos.getMarketUploadServer'
        try:
            return requests.get(
                uri, params=self.common_params, headers=self.headers
            ).json()['response']['upload_url']
        except Exception as e:
            logger.exception(e)

    def save_photo(self, server, photo_json, hash):
        uri = 'https://api.vk.com/method/photos.saveMarketPhoto'
        params = self.common_params
        params.update({
            'photo': photo_json,
            'server': server,
            'hash': hash,
        })
        return requests.get(uri, headers=self.headers, params=params).json()

    def _get_product_url(self, product):
        base_url = settings.BASE_URL.rstrip('/')
        return f'{base_url}{product.get_absolute_url()}'

    def _get_product_description(self, product):
        description = product.description or product.short_description
        if description:
            text = strip_tags(description)
            return Truncator(text).chars(config.VK_MAKET_DESCR_CHARS_LIMIT)
        return product.name

    def _get_product_del_status(self, product):
        """
        Если стоит настройка "выгружать отмеченные" или "выгружать в наличии" и
        товар перестал быть отмеченным или в наличии,
        то передавать параметр deleted=1.
        """
        if ((config.VK_MARKET_UNLOAD_VARIANT == UNLOAD_VARIANT_CHECKED and not product.vk_market) or
                (config.VK_MARKET_AVAIL_ONLY and not product.is_available())):
            return 1
        return 0

    def _upload_product_images(self, product):
        upload_url = self.get_upload_url()

        if not upload_url:
            msg = _('Ошибка получения адреса сервера для загрузки '
                    'фото для товара %(product)s.\n'
                    'Полученный ответ от ВК: %(upload_url)s') % {
                'product': product,
                'upload_url': upload_url
            }
            logger.error(msg)
            return

        ids_list = []

        images_qs = product.images.all()
        for img in images_qs[:self.VK_MARKET_IMG_LIMIT]:
            with open(img.image.path, 'rb') as f:
                r = requests.post(upload_url, files={'file': f})

            r_json = r.json()
            server = r_json.get('server')
            photo_json = r_json.get('photo')
            hash = r_json.get('hash')

            s_json = self.save_photo(server, photo_json, hash)

            img_list = s_json.get('response')

            if not img_list:
                err_msg = _('Не удалось загружить фото для товара %(product)s.\n'
                            'Ответ от VK: %(s_json)s') % {
                    'product': product,
                    's_json': s_json
                }
                logger.error(err_msg)
                continue
            try:
                ids_list.append(img_list[0]['id'])
            except (IndexError, KeyError) as e:
                err_msg = _('Не удалось получить ID фото для товара %(product)s') % {
                    'product': product}
                logger.error(err_msg)
                logger.exception(e)
                continue

        return ids_list

    def _get_product_params(self, product):
        category = product.categories.filter(
            vk_group_id__isnull=False).exclude(vk_group_id=0).first()
        if not category:
            err_msg = _('Среди категорий товара %(product)s нет таких, '
                        'у которых задано соответствие с категориями VK-маркета.') % {'product': product}
            logger.error(err_msg)
            return {}

        photo_ids_list = self._upload_product_images(product)

        if not photo_ids_list:
            err_msg = _('Проблемы с загрузкой изображений для товара %(product)s.') % {
                'product': product}
            logger.error(err_msg)
            return

        params = {
            'name': product.name,
            'description': self._get_product_description(product),
            'main_photo_id': photo_ids_list[0],
            'sku': product.sku,
            'category_id': category.vk_group_id,
            'url': self._get_product_url(product),
            'deleted': self._get_product_del_status(product)
        }

        if len(photo_ids_list) > 1:
            params['photo_ids'] = ','.join(
                [str(i) for i in photo_ids_list[1:]])
        if hasattr(product, 'vk_product'):
            params['item_id'] = product.vk_product.vk_id

        if product.price:
            params['price'] = str(product.currency_price)
            if product.old_price and product.old_price > product.price:
                params['old_price'] = str(product.currency_old_price)
        if product.width:
            params['dimension_width'] = product.width
        if product.height:
            params['dimension_height'] = product.height
        if product.length:
            params['dimension_length'] = product.length
        if product.weight:
            params['weight'] = round(product.weight * 1000)

        return params

    def add(self, product, edit=False):
        """
        Параметры
        owner_id (integer)
            Обязательный параметр. Идентификатор владельца товара.
            Идентификатор сообщества должен начинаться со знака -.

        name (string)
            Обязательный параметр. Название товара.
            Ограничение по длине считается в кодировке cp1251.

        description (text)
            Обязательный параметр. Описание товара.

        category_id (positive)
            Обязательный параметр. Идентификатор категории товара.

        price (string)
            Необязательный параметр. Цена товара.

        old_price (string)
            Необязательный параметр. Старая цена товара.

        deleted (checkbox)
            Необязательный параметр. Статус товара. Возможные значения:
            1 — товар недоступен.
            0 — товар доступен.

        main_photo_id (positive)
            Необязательный параметр. Идентификатор фотографии обложки товара.
            Фотография должна быть загружена согласно инструкции в разделе
            "Загрузка фотографии для товара".

        photo_ids (string)
            Необязательный параметр.
            Идентификаторы дополнительных фотографий товара, перечисленные через запятую.
            Фотография должна быть загружена согласно инструкции в разделе
            "Загрузка фотографии для товара".

        video_ids (string)

        url (string)
            Необязательный параметр. Ссылка на сайт товара.

        dimension_width (positive)
            Необязательный параметр. Ширина в миллиметрах.

        dimension_height (positive)
            Необязательный параметр. Высота в миллиметрах.

        dimension_length (positive)
            Необязательный параметр. Глубина в миллиметрах.

        weight (positive)
            Необязательный параметр. Вес в граммах.

        sku (string)
            Необязательный параметр. Артикул товара (произвольная строка).


        Результат
        Метод возвращает идентификатор добавленного товара (string).
        Пример ответа:
        JSON{
          "response": "1"
        }
        """
        if not product.main_image:
            err_msg = _('У товара %(product)s отсутствуют фото.') % {
                'product': product}
            logger.error(err_msg)
            return

        if edit:
            uri = f'{self.VK_API_MAIN_URI}/market.edit'
        else:
            uri = f'{self.VK_API_MAIN_URI}/market.add'

        product_params = self._get_product_params(product)

        if not product_params:
            err_msg = _('У товара %(product)s отсутствуют обязательные '
                        'параметры для его передачи на VK.') % {'product': product}
            logger.error(err_msg)
            return

        params = self.common_params

        params.update(product_params)

        resp = requests.post(uri, params=params, headers=self.headers)

        result = market_id = vk_response_error = None

        try:
            vk_response_data = resp.json().get('response')
            if vk_response_data:
                if edit and vk_response_data == 1:
                    market_id = product.vk_product.vk_id
                else:
                    market_id = vk_response_data['market_item_id']
            else:
                vk_response_error = True
        except Exception as e:
            vk_response_error = True
            logger.exception(e)

        if vk_response_error:
            err_msg = _('Ответ с ошибкой от VK: %(resp)s') % {'resp': resp}
            if hasattr(resp, 'text'):
                err_msg += f'\n{resp.text}'
            if hasattr(resp, 'data'):
                err_msg += f'\n{resp.data}'
            logger.error(err_msg)
            debug_msg = _('Параметры запроса: %(params)s\nЗаголовки запроса: %(headers)s') % {
                'params': params,
                'headers': self.headers
            }
            logger.error(debug_msg)
            return

        if not hasattr(product, 'vk_product'):
            result = VKProductMembership.objects.create(
                product=product,
                vk_id=market_id
            )
        else:
            result = product.vk_product

        if result:
            if edit:
                logger_msg = _('Товар %(result_product_name)s успешно отредактирован, '
                               'и сохранен в VK-маркете с ID %(result_vk_id)s') % {
                    'result_product_name': result.product.name,
                    'result_vk_id': result.vk_id
                }
            else:
                logger_msg = _('Товар %(result_product_name)s успешно добавлен в '
                               'VK-маркет с ID %(result_vk_id)s') % {
                    'result_product_name': result.product.name,
                    'result_vk_id': result.vk_id
                }
            logger.info(logger_msg)
        else:
            err_msg = _(
                'Добавить товар %(product)s в VK-маркет не удалось.') % {'product': product}
            logger.error(err_msg)

        return result

    def edit(self, product):
        """
        Параметры

        owner_id (integer)
            Обязательный параметр. Идентификатор владельца товара.
            Идентификатор сообщества должен начинаться со знака -.

        item_id (positive)
            Обязательный параметр. Идентификатор товара.

        name (string)
            Необязательный параметр. Новое название товара.

        description (text)
            Необязательный параметр. Новое описание товара.

        category_id (positive)
            Необязательный параметр. Идентификатор категории товара.

        price (string)
            Необязательный параметр. Цена товара.

        old_price (string)
            Необязательный параметр. Старая цена товара.

        deleted (checkbox)
            Необязательный параметр. Статус товара. Возможные значения:
            1 — товар недоступен.
            0 — товар доступен.

        main_photo_id (positive)
            Необязательный параметр. Идентификатор фотографии для обложки товара.
            Фотография может быть загружена с помощью метода photos.getMarketUploadServer.

            Идентификатор фотографии можно получить:
            Загрузив фотографию товара.
            Вызвав методы market.get или market.getById,
            если вы хотите использовать существующую фотографию товара.

        photo_ids (string)
            Необязательный параметр. Идентификаторы дополнительных фотографий товара.
            Идентификатор фотографии можно получить, загрузив фотографию товара.

        url (string)
            Необязательный параметр. Ссылка на сайт товара.

        dimension_width (positive)
            Необязательный параметр. Ширина в миллиметрах.

        dimension_height (positive)
            Необязательный параметр. Высота в миллиметрах.

        dimension_length (positive)
            Необязательный параметр. Глубина в миллиметрах.

        weight (positive)
            Необязательный параметр. Вес в граммах.

        sku (string)
            Необязательный параметр. Артикул товара (произвольная строка).

        Результат
        Метод возвращает 1, если информация товара изменена, и 0 в случае ошибки.
        Пример ответа:
        JSON{
          "response": 1
        }
        """
        return self.add(product, edit=True)

    def delete(self, product):
        """
        Параметры
        owner_id (integer)
            Идентификатор владельца товара.
            Обратите внимание, идентификатор сообщества в параметре owner_id
            необходимо указывать со знаком «-» — например, owner_id=-1 соответствует
            идентификатору сообщества ВКонтакте API (club1).

        item_id (positive)
            Идентификатор товара.

        Результат
        После успешного выполнения возвращает 1.
        """
        if not hasattr(product, 'vk_product'):
            logger.error(f'Товар {product} не может быть удален, '
                         'т.к. не был добавлен в VK-Маркет.')
            return

        uri = f'{self.VK_API_MAIN_URI}/market.delete'
        params = self.common_params
        params['item_id'] = product.vk_product.vk_id

        resp_json = requests.post(
            uri, params=params, headers=self.headers).json()

        if resp_json.get('response') == 1:
            product.vk_product.delete()
            msg = _(
                'Товар %(product)s успешно удален из VK-Маркета.') % {'product': product}
            logger.info(msg)
        else:
            msg = _('Ошибка удаления товара %(product)s из VK-Маркета.\n'
                    'Ответ VK: %(resp_json)s.') % {'product': product, 'resp_json': resp_json}
            logger.error(msg)
