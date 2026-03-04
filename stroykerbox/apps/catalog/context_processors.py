from constance import config

from stroykerbox.apps.catalog import CatalogStatictextKeys
from stroykerbox.apps.catalog.models import Currency


def catalog_context(request):
    currency_default = Currency.get_default()
    return {
        'show_availability_status': not config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE
        or all(
            (
                config.PRODUCT_ALLOW_SALE_NOT_AVAIBLE,
                config.PRODUCT_NOT_AVAIBLE_STATUS_NAME,
            )
        ),
        'currency_symbol': getattr(currency_default, 'symbol', '₽'),
        'catalog_statictext_keys': {i.name: i.value for i in CatalogStatictextKeys},
    }
