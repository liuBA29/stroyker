from enum import Enum

default_app_config = 'stroykerbox.apps.catalog.apps.CatalogConfig'

RECENTLY_WATCHED_SESS_KEY = 'recently_watched'


class CatalogStatictextKeys(Enum):
    CATALOG_PAGE_BLOCK_BEFORE_PREVIEW = (
        'catalog_page_block_before_preview',
        'Страница каталога с подкатегориями/с товарами (если включен CATALOG_SHOW_CHILDS_IN_PARENT) - над превью',
    )
    CATALOG_PAGE_BLOCK_AFTER_PREVIEW = (
        'catalog_page_block_after_preview',
        (
            'Страница каталога с подкатегориями/с товарами (если включен CATALOG_SHOW_CHILDS_IN_PARENT)'
            ' - под превью и над баннерами, набором товаров и сео-текстом.'
        ),
    )
    CATALOG_PAGE_BLOCK_BEFORE_PRODUCTS = (
        'catalog_page_block_before_products',
        'Страница каталога с товарами (конечные категории) - над товарами.',
    )
    CATALOG_PAGE_BLOCK_AFTER_PRODUCTS = (
        'catalog_page_block_after_products',
        (
            'Страница каталога с товарами (конечные категории) - под основными '
            'товарами и над баннерами, набором товаров и сео-текстом.'
        ),
    )

    def __new__(cls, value, description):
        member = object.__new__(cls)
        member._value_ = value
        member.description = description  # type: ignore
        return member
