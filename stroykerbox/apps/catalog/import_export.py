import re
from itertools import zip_longest
from logging import getLogger
import os
from collections import defaultdict
import uuid
from typing import Optional
import xml.etree.ElementTree as ET

import tablib
import requests
from PIL import Image
from django.db.models import (
    Case,
    F,
    Value,
    When,
    Max,
    Count,
    CharField,
    DecimalField,
)
from django.core.files.base import ContentFile
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.files.uploadedfile import InMemoryUploadedFile

from stroykerbox.apps.catalog.models import ProductQuerySet, Product
from stroykerbox.apps.common.services.checker import CommonChecker

from . import models

logger = getLogger(__name__)


EXPORT_IMPORT_MAIN_FORMAT = 'xls'


PRODUCT_SKU_LABEL = 'артикул товара'
PRODUCT_NAME_LABEL = 'название товара'
PARAM_NAME_LABEL = 'название параметра'
PARAM_VALUE_STR_LABEL = 'строковое значение параметра'
PARAM_VALUE_DECIMAL_LABEL = 'цифровое значение параметра'

PRODUCTPARAMETERVALUE_MAP = {
    'product__sku': PRODUCT_SKU_LABEL,
    'product__name': PRODUCT_NAME_LABEL,
    'parameter__name': PARAM_NAME_LABEL,
    'parameter_value_str': PARAM_VALUE_STR_LABEL,
    'parameter_value_decimal': PARAM_VALUE_DECIMAL_LABEL,
}


def get_img_extension(img_byte_obj: bytes) -> Optional[str]:
    try:
        image = Image.open(img_byte_obj)
    except (OSError, IOError):
        return None

    extension = image.format
    if isinstance(extension, str):
        extension = extension.lower()

    if extension == 'jpeg':
        extension = 'jpg'
    return extension


def get_img_filename(
    img_str: str, img_byte_obj: bytes, extension_default: Optional[str] = None
) -> Optional[str]:

    name = img_str.split('/')[-1].split('?')[0] or f'{uuid.uuid4().hex[:8]}'
    extension: Optional[str] = name.split('.')[-1]
    if extension == name:
        extension = extension_default or get_img_extension(img_byte_obj)

    if not all((name, extension)):
        return None

    return f'{name}.{extension}'


def productparametervaluemembership_export(queryset, ext=EXPORT_IMPORT_MAIN_FORMAT):
    data = queryset.annotate(
        parameter_value_str=Case(
            When(parameter__data_type='str', then=F('parameter_value__value_str')),
            output_field=CharField(),
            default=Value(''),
        ),
        parameter_value_decimal=Case(
            When(parameter__data_type='decimal', then=F('value_decimal')),
            output_field=DecimalField(),
            default=Value(None),
        ),
    ).values_list(*PRODUCTPARAMETERVALUE_MAP.keys())
    dst = tablib.Dataset(*data, headers=PRODUCTPARAMETERVALUE_MAP.values())
    return dst.export(ext)


def productparametervaluemembership_import(
    file: InMemoryUploadedFile, delete_before=False
):
    messages = defaultdict(list)
    skiped = membership_created = param_created = 0
    param_values_created = deleted_obj = updated_values = 0
    imported_data = tablib.Dataset().load(file)

    product_processed = []

    for idx, item in enumerate(imported_data.dict, 2):
        sku = re.sub(r'\.0$', '', str(item.get(PRODUCT_SKU_LABEL, '')))
        param_name = item.get(PARAM_NAME_LABEL)
        param_val_str = str(item.get(PARAM_VALUE_STR_LABEL, '') or '')
        param_val_decimal = str(item.get(PARAM_VALUE_DECIMAL_LABEL, '') or '')

        if not all((sku, param_name, any((param_val_str or param_val_decimal)))):
            skiped += 1
            messages['ERROR'].append(f'(строка {idx}) Отсутствуют обязательные данные.')
            continue

        try:
            product_obj = models.Product.objects.get(sku=sku)
        except models.Product.DoesNotExist:
            skiped += 1
            messages['ERROR'].append(
                f'(строка {idx}) Товар с артикулом {sku} не найден.'
            )
            continue

        if delete_before and product_obj not in product_processed:
            deleted, __ = (
                models.ProductParameterValueMembership.objects.filter(
                    product=product_obj
                )
                .exclude(product__in=product_processed)
                .delete()
            )
            deleted_obj += deleted
            product_processed.append(product_obj)

        parameter_obj = models.Parameter.objects.filter(name__iexact=param_name).first()
        if not parameter_obj:
            data_type = 'decimal' if param_val_decimal else 'str'
            parameter_obj = models.Parameter(name=param_name, data_type=data_type)
            parameter_obj.save()
            param_created += 1

        defaults = {}

        parameter_value_obj = None

        if param_val_decimal:
            defaults['value_decimal'] = param_val_decimal
        else:
            try:
                parameter_value_obj = models.ParameterValue.objects.get(
                    parameter=parameter_obj, value_str=param_val_str
                )
            except models.ParameterValue.DoesNotExist:
                parameter_value_obj = models.ParameterValue(
                    parameter=parameter_obj, value_str=param_val_str
                )
                parameter_value_obj.save()
                param_values_created += 1

        try:
            membership, created = (
                models.ProductParameterValueMembership.objects.update_or_create(
                    product=product_obj, parameter=parameter_obj, defaults=defaults
                )
            )
        except ValidationError as e:
            messages['ERROR'].append(f'(строка {idx}) {e}.' f'\n{defaults}')
            membership = created = None
            skiped += 1

        if created:
            membership_created += 1
        elif membership is not None:
            updated_values += 1

        if membership and parameter_value_obj:
            membership.parameter_value.add(parameter_value_obj)

    messages['INFO'].append(
        f'Новых значений товара: {membership_created}'
        f'<br/>Обновлено значений: {updated_values}'
        f'<br/>Новых параметров: {param_created}'
        f'<br/>Новых значений параметров: {param_values_created}'
        f'<br/>Пропущено: {skiped}'
        f'<br/>Удалено объектов: {deleted_obj}'
    )
    return messages


def get_file_from_url(file_url: str):
    headers = {
        'Accept': (
            'text/html,application/xhtml+xml,application/xml;q=0.9,'
            'image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
        ),
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Referer': (
            'https://www.zara.com/uk/en/zw-collection-asymmetric-dress-with-knots-p08686244.html?'
            'v1=306349632&v2=2290847'
        ),
        'Sec-Ch-Ua': '"Chromium";v="117", "Not;A=Brand";v="8"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Linux"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': (
            'Mozilla/5.0 (X11; Linux x86_64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
        ),
    }
    try:
        response = requests.get(file_url, headers=headers, verify=False)
    except Exception as e:
        logger.exception(e)
        return
    if response.status_code == 200:
        return ContentFile(response.content)


def product_images_import(
    file: InMemoryUploadedFile,
    has_headers=False,
    rewrite_images=False,
    resize_width=None,
    extension_default: Optional[str] = None,
):
    messages = defaultdict(list)
    skiped = created = deleted = 0
    imported_data = tablib.Dataset().load(file, headers=has_headers)

    data = []
    for idx, item in enumerate(imported_data.dict, 2):
        data_list = list(item.values()) if has_headers else item
        sku = str(data_list[0]).replace('.0', '')
        props = data_list[1:]
        if not sku:
            continue
        data.append(
            (
                idx,
                sku,
                props,
            )
        )

    products_qs = models.Product.objects.filter(
        sku__in=(sku for idx, sku, props in data)
    ).prefetch_related('images')
    products = {p.sku: p for p in products_qs}

    messages['ERROR'].extend(
        f'(строка {idx}) Товар с артикулом {sku} не найден.'
        for idx, sku, props in data
        if sku not in products
    )

    data = [(idx, sku, props) for idx, sku, props in data if sku in products]

    for idx, sku, props in data:
        product = products[sku]

        exist_qs = product.images.all()

        if rewrite_images:
            deleted_obj, _ = exist_qs.delete()
            deleted += deleted_obj
            max_position = 0
        else:
            max_position = (
                exist_qs.aggregate(Max('position')).get('position__max', 0) or 0
            )

        for img_idx, img_row in enumerate(props, 1):

            if not img_row or not isinstance(img_row, str):
                skiped += 1
                continue
            else:
                idx = img_idx
                for img in img_row.split(','):
                    img = img.strip()
                    position = max_position + idx

                    prod_img = models.ProductImage(product=product, position=position)

                    if img.startswith('http'):
                        img_file = get_file_from_url(img)
                        if img_file:
                            filename = get_img_filename(
                                img, img_file, extension_default
                            )
                            if not filename:
                                skiped += 1
                                continue
                            prod_img.image.save(filename, img_file, save=True)
                            if resize_width:
                                prod_img.resize_image(resize_width)
                            created += 1
                        else:
                            messages['ERROR'].append(
                                f'(строка {idx}) Oшибка получения файла по URL {img}'
                            )
                            skiped += 1
                            continue
                    else:
                        img = img.strip('/')
                        file_path = os.path.join(settings.MEDIA_ROOT, img)
                        if os.path.exists(file_path):
                            prod_img.image.name = img
                            prod_img.save()
                            if resize_width:
                                prod_img.resize_image(resize_width)
                            created += 1
                    try:
                        prod_img.clean()
                        prod_img.update_file_size_value()
                    except ValidationError as e:
                        messages['ERROR'].append(str(e))
                        prod_img.delete()
                        created -= 1
                        skiped += 1
                    except Exception:
                        pass

                    idx += 1

    messages['INFO'].append(
        f'Новых изображений: {created}'
        f'\nПропущено: {skiped}'
        f'\nУдалено объектов: {deleted}'
    )
    if rewrite_images and created:
        call_command('thumbnail', 'clear_delete_referenced', verbosity=0)
    return messages


def product_props_import(file: InMemoryUploadedFile, rewrite_props=None):
    messages = defaultdict(list)
    skiped = created = updated = deleted = 0
    imported_data = tablib.Dataset().load(file, headers=False)

    for idx, data_list in enumerate(imported_data.dict):
        if not idx:
            continue
        sku = str(data_list[0]).replace('.0', '')
        if not sku:
            continue
        try:
            product = models.Product.objects.get(sku=sku)
        except models.Product.DoesNotExist:
            messages['ERROR'].append(
                f'(строка {idx}) Товар с артикулом {sku} не найден.'
            )
            skiped += 1
            continue

        exist_qs = models.ProductProps.objects.filter(product=product)

        if rewrite_props:
            deleted_obj, _ = exist_qs.delete()
            deleted += deleted_obj

        for prop_name, prop_value in zip(data_list[1::2], data_list[2::2]):
            if not all((prop_name, prop_value)):
                continue
            if not rewrite_props and exist_qs.filter(name=prop_name).exists():
                messages['INFO'].append(
                    f'(строка {idx}) Свойство "{prop_name}" для товара с '
                    f'артикулом {sku} уже существует, пропуск.'
                )
                skiped += 1
                continue
            obj = models.ProductProps(product=product, name=prop_name, value=prop_value)
            obj.save()
            created += 1

    messages['INFO'].append(
        f'Новых свойств: {created}'
        f'\nПропущено: {skiped}'
        f'\nОбновлено: {updated}'
        f'\nУдалено объектов: {deleted}'
    )
    return messages


def product_props_export(queryset, ext=EXPORT_IMPORT_MAIN_FORMAT):
    data = []
    qs = queryset.filter(props__isnull=False)
    if qs.exists():
        max_props = (
            qs.annotate(num_props=Count('props')).earliest('-num_props').num_props
        )
    else:
        max_props = 0

    # вычисляем необходимое количество колонок
    # макс. колл-во * 2 (ключ и значение)
    max_cols = max_props * 2
    # + 1 (колонка с артикулом товара и его названием)
    max_cols += 2

    headers = ['артикул товара', 'название товара']
    for __ in range(max_props):
        headers += ['свойство', 'значение']

    for product in qs.distinct():
        row = [product.sku, f'{product.name}']
        for prop in product.props.all():
            row += [prop.name, prop.value]
        len_cols = len(row)
        if len_cols < max_cols:
            row += ['' for __ in range(max_cols - len_cols)]
        data.append(row)

    dst = tablib.Dataset(*data, headers=headers)
    return dst.export(ext)


def export_parameter_values(parameter_pk, ext=EXPORT_IMPORT_MAIN_FORMAT):
    try:
        parameter = models.Parameter.objects.get(pk=parameter_pk)
    except models.Parameter.DoesNotExist:
        return

    headers = ('value_str', 'value_slug', 'position')

    data = parameter.values.values_list(*headers)
    dst = tablib.Dataset(*data, headers=headers)
    return dst.export(ext)


def import_parameter_values(parameter_pk, file):
    try:
        parameter = models.Parameter.objects.get(pk=parameter_pk)
    except models.Parameter.DoesNotExist:
        return

    messages = defaultdict(list)
    skiped = created = updated = 0

    imported_data = tablib.Dataset().load(file)

    for idx, row in enumerate(imported_data.dict, 2):
        if not row['value_slug']:
            skiped += 1
            messages['ERROR'].append(f'(строка {idx}) Отсутствуют обязательные данные.')
            continue
        try:
            obj, new = models.ParameterValue.objects.update_or_create(
                parameter=parameter,
                value_slug=row['value_slug'],
                defaults={'value_str': row['value_str'], 'position': row['position']},
            )
        except Exception as e:
            skiped += 1
            messages['ERROR'].append(f'(строка {idx}) {e}.')
            continue
        if new:
            created += 1
        else:
            updated += 1

    messages['INFO'].append(
        f'Новых значений: {created}' f'\nОбновлено: {updated}' f'\nПропущено: {skiped}'
    )
    return messages


def product_doc_export(queryset, ext=EXPORT_IMPORT_MAIN_FORMAT):
    data = []
    if queryset.exists():
        max_docs = (
            queryset.annotate(num_docs=Count('certificates'))
            .earliest('-num_docs')
            .num_docs
        )
    else:
        max_docs = 0

    # вычисляем необходимое количество колонок
    # макс. колл-во * 2 (ключ и значение)
    max_cols = max_docs * 2
    # + 1 (колонка с артикулом товара)
    max_cols += 1

    headers = ['артикул товара']
    for __ in range(max_docs):
        headers += ['название', 'ссылка']

    for product in queryset.distinct():
        row = [product.sku]
        for doc in product.certificates.all():
            row += [doc.name, doc.file.url]
        len_cols = len(row)
        if len_cols < max_cols:
            row += ['' for __ in range(max_cols - len_cols)]
        data.append(row)

    dst = tablib.Dataset(*data, headers=headers)
    return dst.export(ext)


def product_doc_import(file, delete_old=None):
    messages = defaultdict(list)
    skiped = created = deleted = 0
    imported_data = tablib.Dataset().load(file, headers=False)

    doc_processed_ids = []

    for idx, items in enumerate(imported_data.dict, 1):
        if not items or len(items) < 3:
            if idx > 1:  # на случай, если заголовки таки будут
                messages['ERROR'].append(
                    f'(строка {idx}) Для товара с артикулом {items[0]} не указано документов.'
                )
                skiped += 1
            continue
        try:
            product = models.Product.objects.get(sku=items[0])
        except models.Product.DoesNotExist:
            if idx > 1:  # на случай, если заголовки таки будут
                messages['ERROR'].append(
                    f'(строка {idx}) Товара с артикулом {items[0]} не найдено.'
                )
                skiped += 1
            continue

        docs_list = items[1:]

        for i in zip_longest(docs_list[0::2], docs_list[1::2]):
            try:
                file = i[1].lstrip(settings.MEDIA_URL).strip('/')
                if not file:
                    continue
                file_path = os.path.join(settings.MEDIA_ROOT, file)
                if os.path.isfile(file_path):
                    obj = models.ProductCertificate(product=product, name=i[0])
                    obj.file.name = file
                    obj.save()
                    created += 1
                    if delete_old:
                        doc_processed_ids.append(obj.id)
                        del_count, __ = (
                            models.ProductCertificate.objects.filter(product=product)
                            .exclude(id__in=doc_processed_ids)
                            .delete()
                        )
                        deleted += del_count
                else:
                    messages['ERROR'].append(
                        f'(строка {idx}): Файл внутри медиа-дерректории по пути {file} не обнаружен.'
                    )
                    skiped += 1
                    continue
            except Exception as e:
                messages['ERROR'].append(f'(строка {idx}) Ошибка: {e}.')
                skiped += 1
                continue

    messages['INFO'].append(f'Новых документов: {created}' f'\nПропущено: {skiped}')
    if delete_old:
        messages['INFO'].append(f'\nУдалено документов: {deleted}')

    return messages


def product_related_export(
    queryset: ProductQuerySet, ext: str = EXPORT_IMPORT_MAIN_FORMAT
) -> bytes:
    """
    https://redmine.fancymedia.ru/issues/13307#note-2
    """
    qs = queryset.filter(related_products__isnull=False)
    data = []

    for product in qs:
        related_list = product.ref.values_list('product__sku', flat=True).order_by(
            'position'
        )
        data.append((product.sku, ','.join(related_list)))

    dst = tablib.Dataset(*data, headers=('товар', 'связанные'))
    return dst.export(ext)


def product_related_import(
    file: InMemoryUploadedFile, rewrite: Optional[bool] = None
) -> dict[str, list]:
    """
    https://redmine.fancymedia.ru/issues/13307#note-2
    """
    messages = defaultdict(list)
    edited = 0
    imported_data = tablib.Dataset().load(file)

    for idx, data in enumerate(imported_data, 1):
        try:
            product_sku = data[0]
            related_sku = data[1]
            related_sku_list = str(data[1]).split(',') if related_sku else None
        except KeyError:
            continue

        try:
            product = models.Product.objects.get(sku=product_sku)
        except models.Product.DoesNotExist:
            messages['ERROR'].append(
                f'(строка {idx}) Товара с артикулом {product_sku} не существует.'
            )
            continue

        # https://redmine.nastroyker.ru/issues/13616
        if rewrite:
            models.ProductRelated.objects.filter(ref__sku=product_sku).delete()

        if related_sku_list:
            for position, rel_sku in enumerate(related_sku_list, 1):
                try:
                    rel_product = models.Product.objects.get(sku=rel_sku)
                except models.Product.DoesNotExist:
                    messages['ERROR'].append(
                        f'(строка {idx}) Связываемого товара с артикулом {rel_sku} не существует.'
                    )
                    continue
                models.ProductRelated.objects.update_or_create(
                    ref=product,
                    product=rel_product,
                    defaults={'position': position},
                )
                edited += 1

    messages['INFO'].append(f'Обновлено товаров: {edited}')

    return messages


def update_prices_from_feed(url, sku_field) -> dict:
    output = defaultdict(list)
    response = requests.get(url)
    if response.status_code != 200:
        output['ERROR'].append(
            f'Ошибка получения данных. Статус ответа: {response.status_code}'
        )
    elif 'xml' not in response.headers.get('Content-Type', ''):
        output['ERROR'].append(
            f'Неподдерживаемый тип содержимого: {response.headers["Content-Type"]}'
        )

    if 'ERROR' in output:
        return output

    updated = 0

    try:
        tree = ET.fromstring(response.text)
        for offer in tree.find('shop').find('offers'):  # type: ignore
            sku = (
                offer.attrib.get('id')
                if sku_field == 'offerId'
                else getattr(offer.find('vendorCode'), 'text', None)
            )
            price = getattr(offer.find('price'), 'text', None)

            if not all((sku, price)):
                continue

            updated += models.Product.objects.filter(sku=sku).update(price=price)

    except Exception as e:
        output['ERROR'].append(str(e))
    else:
        output['INFO'].append(f'Обновлено цен у {updated} товара(ов)')

    return output


def replace_product_sku(file: InMemoryUploadedFile) -> dict:
    updated = 0
    output = {}
    try:
        data = tablib.Dataset().load(file, headers=False)
        for item in data.dict:
            updated += models.Product.objects.filter(sku=item[0]).update(sku=item[1])
    except Exception as e:
        output['ERROR'] = str(e)
    else:
        if updated > 0:
            output['INFO'] = f'Обновлено артикулов: {updated}'
        else:
            output['INFO'] = 'Не обновлено ни одного артикула.'
    return output


def heavy_picture_products_export(ext=EXPORT_IMPORT_MAIN_FORMAT):
    """
    https://redmine.nastroyker.ru/issues/19460
    """
    max_size = CommonChecker.MAX_ALLOWED_IMG_SIZE_MB * 1048576
    headers = ('sku', 'name', 'max_img_size_mb')
    qs = (
        Product.objects.filter(images__image_file_size__gt=max_size).annotate(
            max_img_size_mb=Max('images__image_file_size')
        )
    ).values_list(*headers)
    data = [
        (sku, name, round(max_img_size / 1048576, 1)) for sku, name, max_img_size in qs
    ]
    dst = tablib.Dataset(*data, headers=headers)
    return dst.export(ext)
