from typing import Any
import json
import hashlib
from logging import getLogger
from urllib.request import urlopen
from tempfile import NamedTemporaryFile

from django.core.files import File

from constance import config
from uuslug import uuslug
from stroykerbox.apps.catalog.models import (
    Product,
    Category,
    ParameterValue,
    ProductParameterValueMembership,
    CategoryParameterMembership,
    ProductProps,
    ProductImage,
    Stock,
    ProductStockAvailability,
)

from .models import SubcategoryAsParameter, UpdateLog


logger = getLogger(__name__)


class LombardHelper:
    """
    Manual for the Shop: https://docs.google.com/document/d/1CEgd4_QfCwIKbTNkxi_xBwuKFztBBg6LISfOdq4eAn8/edit
    Push API docs: https://docs.google.com/document/d/1XctmPBlRVIguk8OnKaV7UZMj64Qlz4NckhzilKnnVwo/edit
    """

    def __init__(self, request, **kwargs):
        self.request = request
        self.data = request.POST.get('data')
        self.response_messages = []
        self.log = UpdateLog.objects.create()
        self.json_data = self.get_json_data()

        logger.debug(f'JSON data: {self.json_data}')

    def get_json_data(self):
        try:
            return json.loads(self.data)
        except Exception as e:
            logger.exception(e)
            self.log.write(e)
        return {}

    def is_valid(self):
        headers_hash = self.request.headers.get('Authorizationsl', '')
        own_hash = hashlib.sha1(
            bytes(
                hashlib.sha1(bytes(self.data, 'utf-8')).hexdigest()
                + config.SMARTLOMBARD_SECRET_KEY,
                'utf-8',
            )
        ).hexdigest()
        valid = headers_hash == own_hash

        if valid:
            logger.debug(
                f'Validation success: headers_hash: {headers_hash}, \nown_hash: {own_hash}'
            )
            return True
        else:
            logger.error(
                f'Validation failed. Request Headers: {self.request.headers}'
                f'\nOwn Hash from data: {own_hash}'
            )
            self.response_messages.append(
                {'status': False, 'type': 'auth', 'message': 'Authorization failed'}
            )
        return False

    def merchant_is_removed(self, merch_data):
        """
        Действия при отключении (удалении) инстанса магазина.
        Снимаем с публикации все товары.
        """
        workplace_code = merch_data['data'].get('workplace')
        if workplace_code:
            for item in ProductStockAvailability.objects.filter(
                warehouse__third_party_code=workplace_code
            ):
                item.product.published = False
                item.product.save(update_fields=('published',))
            self.log.write(
                f'Merchang with workplace code {workplace_code} is removed. '
                'All product availability objects linkid with this store have been unpublished.'
            )

    def parse_merchants(self, merchants):
        if merchants is None:
            return

        try:
            for merch in merchants:
                action_type = merch.get('type')

                if action_type == 'remove':
                    self.merchant_is_removed(merch)

                self.response_messages.append(
                    {
                        'status': True,
                        'type': f'merchant-{action_type}',
                        'unique': merch['data']['workplace'],
                    }
                )

        except Exception as e:
            logger.exception(e)
            self.log.write(e)

    def parse_goods(self):
        new = updated = deleted = zero_price = 0
        for item in self.json_data:
            if not isinstance(item, dict) or 'data' not in item:
                logger.error(f'The Item (front json dict) is not valid: {item}')
                continue
            try:
                merchants = item['data'].get('merchants')
                self.parse_merchants(merchants)

                goods = item['data'].get('goods')

                for good in goods:
                    if self.skip_sync_action(good):
                        continue
                    action = good.get('type')
                    if action in ('add', 'edit'):

                        if not good['data'].get('price', 0):
                            zero_price += 1
                            self.zero_price_action(good)
                            continue
                        _updated, _new = self.update_or_create(good, action=action)
                        updated += _updated
                        new += _new
                    elif good.get('type') == 'remove':
                        deleted += self.remove(good)

            except Exception as e:
                logger.exception(e)
                self.log.write(e)

        if any((new, updated, deleted, zero_price)):
            self.log.write(
                (
                    f'Result: new: {new}, updated: {updated}, deleted: {deleted}, '
                    f'zero price: {zero_price}'
                )
            )

    def skip_sync_action(self, good: dict):
        """
        https://redmine.fancymedia.ru/issues/11791
        есть задача не выгружать из ломбарда на сайт некоторые товары
        т.к. отдельного поля/признака в ломбарде для этого сделать не можем,
        то условились,
            что есть поле "features" начинается строкой "!!!", то этот товар не надо загружать на сайт

        """
        if not isinstance(good, dict) or 'data' not in good:
            return
        features = good['data'].get('features')
        if (
            config.SMARTLOMBARD_FEATURES_STOPPREFIX
            and isinstance(features, str)
            and features.strip().startswith(config.SMARTLOMBARD_FEATURES_STOPPREFIX)
        ):
            # https://redmine.fancymedia.ru/issues/11791#note-3
            # товар со стоп-префиксом снимаем с публикации
            Product.objects.filter(sku=good['data'].get('article')).update(
                published=False
            )
            return True

    def create_product_description(self, good: dict) -> str:
        descr = []
        if good['data'].get('features'):
            descr.append(good['data']['features'])
        if good['data'].get('specifications'):
            text = (
                config.SMARTLOMBARD_PRODUCT_SPEC_PRE_TEXT
                + good['data']['specifications']
            )
            descr.append(text)
        return '\n\n'.join(descr)

    def process_categories(self, product, good_data):
        category = good_data['data'].get('category', '').strip()
        try:
            category = Category.objects.get(name__iexact=category, parent__isnull=True)
        except Category.DoesNotExist:
            logger.error(f'There is no root category named "{category}".')
            return
        except Category.MultipleObjectsReturned:
            logger.error(f'For category "{category}": returned more than one object')
            return

        subcategory_name = good_data['data'].get('subcategory')

        if subcategory_name:
            try:
                category = Category.objects.get(
                    name__iexact=subcategory_name, parent=category
                )
            except Category.DoesNotExist:
                try:
                    subcat_as_param = SubcategoryAsParameter.objects.get(
                        parent_category=category
                    )
                except SubcategoryAsParameter.DoesNotExist:
                    category = Category(name=subcategory_name, parent=category)
                    category.save()
                else:
                    param_val, __ = ParameterValue.objects.get_or_create(
                        parameter=subcat_as_param.parameter, value_str=subcategory_name
                    )
                    if not param_val.value_slug:
                        param_val.value_slug = uuslug(
                            param_val.value_str,
                            instance=param_val,
                            slug_field='value_slug',
                        )
                        param_val.save()
                    product_param_membership, __ = (
                        ProductParameterValueMembership.objects.get_or_create(
                            product=product, parameter=subcat_as_param.parameter
                        )
                    )
                    product_param_membership.parameter_value.add(param_val)
                    CategoryParameterMembership.objects.get_or_create(
                        category=category,
                        parameter=subcat_as_param.parameter,
                        defaults={'display': True, 'position': 0},
                    )

        product.categories.add(category)

    def process_stocks(self, product, good_data):
        withdrawn = good_data['data'].get('withdrawn')
        if (
            good_data['data'].get('hidden')
            or good_data['data'].get('sold')
            or withdrawn
        ):
            ProductStockAvailability.objects.filter(product=product).delete()
            if withdrawn and getattr(product, 'published', None):
                product.published = False
                product.save(update_fields=('published',))
            return

        workplace_code = good_data['data'].get('workplace')
        if workplace_code:
            for stock in Stock.objects.filter(third_party_code=workplace_code):
                ProductStockAvailability.objects.update_or_create(
                    product=product, warehouse=stock, defaults={'available': 1}
                )

    def process_images(self, product, good_data):
        ProductImage.objects.filter(product=product).delete()
        images = good_data['data'].get('images')

        if not images:
            return

        logger.debug(f'Parsing images for the Product {product.name}:\n{images}')

        for img in images:
            if 'src' not in img:
                continue
            img_name = img['src'].split('/')[-1]
            logger.debug(f'Process for image {img_name}')

            try:
                img_temp = NamedTemporaryFile(delete=True)
                img_temp.write(urlopen(img['src']).read())
                img_temp.flush()
                img_obj = ProductImage(product=product)
                img_obj.image.save(img['src'].split('/')[-1], File(img_temp))
                img_obj.save()
            except Exception as e:
                logger.error(e)

    def process_product_props(self, product, good_data):
        """
        Обработка свойств товара.
        """
        props_map = {
            'size': 'размер',
            'metal_name': 'металл',
            'metal_standart_name': 'проба',
        }
        for field, name in props_map.items():
            value = good_data['data'].get(field)
            if value:
                try:
                    ProductProps.objects.update_or_create(
                        product=product, name=name, defaults={'value': value}
                    )
                except ProductProps.MultipleObjectsReturned:
                    ProductProps.objects.filter(product=product, name=name).update(
                        value=value
                    )
                except Exception as e:
                    logger.exception(e)
                    self.log.write(e)

    def zero_price_action(self, good):
        """
        Логика, когда цена товара равна нулю или отсутствует.
        Если такого товара на сейте еще нет, то игнорируем.
        Если есть - обнуляем его цену и снимаем с публикации.
        """
        logger.info(f'Zero price for the Good with data: {good}')
        Product.objects.filter(sku=good['data'].get('article')).update(
            price=0, published=False
        )

        # Обработка на случай, если это тестовый запрос.
        self.response_messages.append(
            {
                'type': f'good-{good.get("type", "")}',
                'unique': good['data'].get('article'),
                'status': True,
            }
        )

    def update_or_create(self, good: dict, action: str):
        lombard_id = good['data'].get('article')
        created = updated = 0
        product_data: dict[str, Any] = {}
        product_data['published'] = bool(not good['data'].get('hidden'))
        product_data['yml_export'] = True

        if 'name' in good['data']:
            product_data['name'] = good['data']['name']
        if 'price' in good['data']:
            product_data['price'] = good['data']['price']

        description = self.create_product_description(good)
        if description:
            product_data['description'] = description

        try:
            product, is_created = Product.objects.update_or_create(
                sku=lombard_id, defaults=product_data
            )
        except Exception as e:
            logger.exception(e)
            self.log.write(e)
        else:
            self.process_categories(product, good)
            self.process_product_props(product, good)
            self.process_images(product, good)
            self.process_stocks(product, good)

            if is_created:
                logger.info(
                    f'Product object with SKU {lombard_id} and name "{product.name}" has been created.'
                )
                created += 1
            else:
                logger.info(
                    f'Product object with SKU {lombard_id} and name "{product.name}" has been updated.'
                )
                updated += 1

        self.response_messages.append(
            {
                'type': f'good-{action}',
                'unique': lombard_id,
                'status': True,
            }
        )
        return (updated, created)

    def create(self, good):
        lombard_id = good['data'].get('article')
        created = 0
        if not Product.objects.filter(sku=lombard_id).exists():
            try:
                product = Product.objects.create(
                    sku=lombard_id,
                    name=good['data'].get('name'),
                    price=good['data'].get('price', 0),
                    description=self.create_product_description(good),
                    published=(not good['data'].get('hidden')),
                )
            except Exception as e:
                logger.exception(e)
                self.log.write(e)
            else:
                logger.info(
                    f'Product object with SKU {lombard_id} and name "{product.name}" has been created.'
                )
                created = 1

                self.process_categories(product, good)
                self.process_product_props(product, good)
                self.process_images(product, good)
                self.process_stocks(product, good)

        else:
            logger.info(f'Product object with SKU {lombard_id} already exist.')

        self.response_messages.append(
            {
                'type': 'good-add',
                'unique': lombard_id,
                'status': True,
            }
        )
        return created

    def process_product_data_dict(self, good_data):
        data = {}
        if 'name' in good_data['data']:
            data['name'] = good_data['data']['name']
        if 'hidden' in good_data['data']:
            data['published'] = not good_data['data'].get('hidden')

        description = self.create_product_description(good_data)
        is_sale = False
        if description:
            data['description'] = description
            is_sale = bool('#акция' in description)

        data['is_sale'] = is_sale
        return data

    def process_product_price(self, product, good_data):
        """
        Манипуляции с ценой (если нужно) при обновлении товара.
        """
        price = good_data['data'].get('price')
        if not price or price == product.price:
            return

        if price < product.price:
            # При цене ниже текущей цены товара переносим текущую цену в
            # "старую цену" и ставим флаг "скидка".
            old_price = product.price
            discounted = True
        else:
            old_price = None
            discounted = False

        product.price = price
        product.old_price = old_price
        product.discounted = discounted
        product.save()

    def edit(self, good):
        lombard_id = good.get('article')
        updated = 0

        product_data = self.process_product_data_dict(good)

        logger.debug(f'Updating the Product with data: {product_data}')
        try:
            product, __ = Product.objects.update_or_create(
                sku=lombard_id, defaults=product_data
            )
        except Exception as e:
            logger.error(f'{e.__class__}: {e}')
            logger.exception(e)
            self.log.write(e)
        else:
            self.process_product_price(product, good)
            self.process_categories(product, good)
            self.process_product_props(product, good)
            self.process_images(product, good)
            self.process_stocks(product, good)

            updated = 1

        self.response_messages.append(
            {
                'type': 'good-edit',
                'unique': lombard_id,
                'status': True,
            }
        )
        return updated

    def remove(self, good):
        lombard_id = good.get('article')
        del_product, __ = Product.objects.filter(sku=lombard_id).delete()

        self.response_messages.append(
            {
                'type': 'good-remove',
                'unique': lombard_id,
                'status': True,
            }
        )
        return del_product
