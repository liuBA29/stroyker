import re
import datetime
import logging
import math
from functools import reduce
import operator

from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db.models import Value
from django.contrib.humanize.templatetags.humanize import intcomma
from constance import config

from stroykerbox.apps.utils.utils import clear_punctuation


logger = logging.getLogger('django')


def update_product_search_index(product):
    if not hasattr(product, 'index_components'):
        return
    components = product.index_components()
    pk = product.pk

    search_vectors = []
    for weight, text in components.items():
        text = clear_punctuation(text)
        search_vectors.append(
            SearchVector(Value(text, output_field=SearchVectorField()),
                         weight=weight, config='russian')
        )
    return product.__class__.objects.filter(pk=pk).update(
        search_document=reduce(operator.add, search_vectors)
    )


def get_dates_prices_for_chart(prices_data):
    dates = []
    prices = []
    today = datetime.datetime.today().date()
    prices_data = list(prices_data)
    try:
        last_date, last_price = prices_data[-1]
    except TypeError:
        return

    prices_data += [(today, last_price)] if last_date != today else []
    for data in prices_data:
        current_created_to, price = data
        if dates:
            prev_created_to = dates[- 1]
            try:
                prev_price = prices[- 1]
            except IndexError:
                prev_price = price
            delta_date = current_created_to - prev_created_to
            if delta_date.days:
                for day in range(1, delta_date.days):
                    dates.append(prev_created_to +
                                 datetime.timedelta(days=day))
                    prices.append(prev_price)
        dates.append(current_created_to)
        try:
            prices.append(float(price))
        except TypeError as e:
            logger.debug(
                f'get_dates_prices_for_chart #632 with empty price: {e}')
    dates = [date.strftime('%d-%m-%Y') for date in dates]
    return dates, prices


def slide_indexes(products, count=8):
    slides_count = int(math.ceil(float(len(products)) / count))
    return range(1, slides_count + 1)


def _all_equal(items):
    """
    Returns True if all the items are equal False otherwise.
    """
    for i in range(1, len(items)):
        if items[i] != items[i - 1]:
            return False

    return True


def clear_categories_menu_template_cache():
    key_names = ('catalog_categories_menu',
                 'catalog_categories_menu_mobile',
                 'catalog_categories_menu_mobile_simple')
    for i in key_names:
        key = make_template_fragment_key(i)
        cache.delete(key)


def has_cyrillic(text):
    return bool(re.search('[а-яА-Я]', text))


def lat2cyr(string, clear=True):
    string = re.sub(r'[^\w\d]', '', string)
    if has_cyrillic(string):
        layout = dict(zip(map(ord,
                          "йцукенгшщзхъфывапролджэячсмитьбю.ё"
                              'ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,Ё'),
                          "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
                          'QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?~'))
    else:
        layout = dict(zip(map(ord, "qwertyuiop[]asdfghjkl;'zxcvbnm,./`"
                                   'QWERTYUIOP{}ASDFGHJKL:"ZXCVBNM<>?~'),
                          "йцукенгшщзхъфывапролджэячсмитьбю.ё"
                          'ЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮ,Ё'))

    return string.translate(layout)


def get_formatted_price(price, use_intcomma=True):
    if price:
        if not config.PRICE_WITH_PENNIES:
            price = int(price)
        price = round(price, 2)

    if use_intcomma:
        price = intcomma(price)

    return price or ''
