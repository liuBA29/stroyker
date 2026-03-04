from typing import Optional
import html
import os
from logging import getLogger
import xml.etree.cElementTree as ET
from xml.etree.ElementTree import Element, SubElement

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q, QuerySet
from constance import config

from stroykerbox.apps.catalog.models import Category, Product
from stroykerbox.apps.catalog.utils import get_formatted_price
from stroykerbox.apps.seo.models import MetaTag
from stroykerbox.apps.locations.models import Location

logger = getLogger('yml_export')


class Command(BaseCommand):
    help = 'Products export to YML'

    def _get_product_name(self, product: Product) -> str:
        if config.YML_NAME_WITH_SKU:
            return f'{product.name.rstrip(".")}, {product.sku}'
        return product.name

    def _get_product_price(self, product: Product) -> int | float | str:
        price = product.online_price() or product.currency_price
        return get_formatted_price(price, False)

    def _get_products(self, **options) -> QuerySet[Product]:
        qs = Product.objects.filter(
            yml_export=True,
            published=True,
            price__isnull=False,
            categories__isnull=False,
        )

        # https://redmine.fancymedia.ru/issues/11889
        # https://redmine.nastroyker.ru/issues/16143
        if not config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE and config.YML_EXCLUDE_NOT_AVAIL:
            qs = qs.exclude(
                Q(stocks_availability__available__isnull=True)
                | Q(stocks_availability__available__lte=0)
            )

        return qs.distinct()

    def get_file_path(self, **options) -> str:
        yml_file_dir = os.path.dirname(settings.YML_EXPORT_FILE_PATH)

        if not os.path.exists(yml_file_dir):
            os.makedirs(yml_file_dir)

        return settings.YML_EXPORT_FILE_PATH

    def get_categories(self, **options) -> QuerySet[Category]:
        return Category.objects.filter(published=True).order_by('pk')

    def get_collection_slug(self, category_object) -> str:
        """
        Уникальный ID каталога, не более 20 символов.
        Может быть числовым, буквенным, буквенно-числовым.
        Идентификаторы для каждого каталога должны быть уникальны.
        """
        return category_object.slug[:20]

    def get_collection_name(self, category_object: Category) -> Optional[str]:
        url = category_object.get_absolute_url()
        try:
            meta_obj = MetaTag.objects.get(url=url)
        except MetaTag.DoesNotExist:
            meta_obj = None
        else:
            return meta_obj.h1

    def get_collection_data(self, category_object: Category) -> dict:
        data = {}
        url = category_object.get_absolute_url()
        try:
            meta_obj = MetaTag.objects.get(url=url)
        except MetaTag.DoesNotExist:
            meta_obj = None

        if meta_obj:
            data['description'] = meta_obj.meta_description
            data['name'] = meta_obj.h1
        else:
            # get category description
            description = category_object.name

            if config.SEO_CATEGORY_META_DESC_PREFIX:
                description = f'{config.SEO_CATEGORY_META_DESC_PREFIX} {description}'
            if config.SEO_CATEGORY_META_DESC_SUFFIX:
                description = f'{description} {config.SEO_CATEGORY_META_DESC_SUFFIX}'

            if description != category_object.name:
                data['description'] = description

            # get category name
            name = category_object.name
            if config.SEO_CATEGORY_META_H1_PREFIX:
                name = f'{config.SEO_CATEGORY_META_H1_PREFIX} {name}'
            if config.SEO_CATEGORY_META_H1_SUFFIX:
                name = f'{name} {config.SEO_CATEGORY_META_H1_SUFFIX}'
            data['name'] = name

        return data

    def get_collections_dict(self, **options) -> dict:
        output = {}
        for c in self.get_categories(**options):
            slug = self.get_collection_slug(c)
            if slug in output or not any((c.image, c.svg_image)):
                continue
            collection_data = self.get_collection_data(c)
            output[slug] = {
                'url': f'{settings.BASE_URL}{c.get_absolute_url()}',
                'picture': f'{settings.BASE_URL}{c.image_file.url}',
                'name': collection_data.get('name', ''),
            }
            if 'description' in collection_data:
                output[slug]['description'] = collection_data['description']
        return output

    def _get_offer_available(
        self, product: Product, location: Optional[Location] = None
    ) -> str:
        """
        https://redmine.fancymedia.ru/issues/11889
        """
        if (
            config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE
            or product.available_items_count(location) > 0
        ):
            return 'true'
        return 'false'

    def handle(self, *args, **options):
        logger.info('------- Start products export to YML without options -------')

        site_address = settings.BASE_URL
        yml_file_path = self.get_file_path(**options)

        generated_on = timezone.localtime(timezone.now())
        root = Element('yml_catalog')
        root.set('date', generated_on.strftime("%Y-%m-%d %H:%M"))
        shop = SubElement(root, 'shop')
        name = SubElement(shop, 'name')
        name.text = config.SITE_NAME
        company = SubElement(shop, 'company')
        company.text = config.SITE_NAME
        url = SubElement(shop, 'url')
        url.text = site_address
        currencies = SubElement(shop, 'currencies')
        currency = SubElement(currencies, 'currency')
        currency.set('id', 'RUR')
        currency.set('rate', '1')

        products = self._get_products(**options)

        categories = SubElement(shop, 'categories')
        for category in self.get_categories(**options):
            id = category.pk
            parent_id = category.parent_id
            name = category.name
            category = SubElement(categories, 'category')
            category.set('id', str(id))
            if parent_id:
                category.set('parentId', str(parent_id))
            category.text = name

        collection_dict = self.get_collections_dict(**options)

        offers = SubElement(shop, 'offers')
        exported = 0
        for product in products:
            if not all((product.price, product.images.count())):
                continue

            product.check_slug()

            product_price = self._get_product_price(product)
            product_categories = product.categories.all()

            try:
                offer = SubElement(offers, 'offer')
                offer.set('id', str(product.pk))
                offer.set('available', self._get_offer_available(product))
                offer_url = SubElement(offer, 'url')
                offer_url.text = f'{site_address}{product.get_absolute_url()}'

                name = SubElement(offer, 'name')
                name.text = html.escape(self._get_product_name(product))

                price = SubElement(offer, 'price')
                price.text = str(product_price)

                currency_id = SubElement(offer, 'currencyId')
                currency_id.text = 'RUR'

                category_id = SubElement(offer, 'categoryId')
                category_id.text = str(product_categories.first().pk)

                picture = SubElement(offer, 'picture')
                picture.text = f'{site_address}{product.images.all().first().image.url}'

                description_text = product.short_description or product.description

                # Признак б/у-шности товара (если задано в глоб. настройках)
                if config.PRODUCTS_IS_RESALE:
                    resale_data = SubElement(offer, 'condition')
                    resale_data.set('type', 'preowned')
                    quality = SubElement(resale_data, 'quality')
                    quality.text = 'excellent'

                if description_text:
                    description = SubElement(offer, 'description')
                    description.text = description_text

                for ppvm in product.params.all():
                    param = SubElement(offer, 'param')
                    param.set('name', ppvm.parameter.name)
                    param.text = str(ppvm.value)
                for prop in product.props.all():
                    param = SubElement(offer, 'param')
                    param.set('name', prop.name)
                    param.text = str(prop.value)

                # collections
                if product_categories.exists():
                    for cat in product_categories:
                        slug = self.get_collection_slug(cat)
                        if slug in collection_dict:
                            collection_id = SubElement(offer, 'collectionId')
                            collection_id.text = slug

                exported += 1
            except Exception as e:
                logger.error(
                    f'Error while export product id={product.pk} name="{product.name}": {str(e)}'
                )

        if collection_dict:
            collections = SubElement(shop, 'collections')
            for slug, data in collection_dict.items():
                collection = SubElement(collections, 'collection')
                collection.set('id', slug)

                c_name = SubElement(collection, 'name')
                c_name.text = data.get('name', '')

                c_url = SubElement(collection, 'url')
                c_url.text = data.get('url', '')

                if 'picture' in data:
                    c_picture = SubElement(collection, 'picture')
                    c_picture.text = data['picture']

                if 'description' in data:
                    c_descr = SubElement(collection, 'description')
                    c_descr.text = data['description']

        tree = ET.ElementTree(root)
        tree.write(
            yml_file_path,
            encoding='utf-8',
            xml_declaration='<?xml version="1.0" encoding="UTF-8"?>',  # type: ignore
        )

        logger.info('Products export finished successfully')
        logger.info(
            f'{exported} products exported to yml from {products.count()} selected'
        )
        logger.info('------- End of export -------')
