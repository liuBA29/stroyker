from django.utils.formats import date_format
from django.utils.translation import ugettext as _
import tablib

# from stroykerbox.apps.commerce.models import Order


def get_order_export_data(queryset, ext='xls'):
    data = []
    headers = [
        _('номер заказа'),
        _('дата заказа'),
        _('артикул товара'),
        _('наименование товара'),
        _('кол-во товара'),
        _('цена товара'),
        _('сумма')
    ]
    for order in queryset.filter(products__isnull=False):
        order_date = date_format(order.created_at)
        for product in order.order_products.all():
            row = [
                order.id,
                order_date,
                product.product.sku,
                product.product.name,
                product.quantity,
                product.product_price,
                (product.product_price * product.quantity)
            ]

            data.append(row)

    dst = tablib.Dataset(*data, headers=headers)
    return dst.export(ext)
