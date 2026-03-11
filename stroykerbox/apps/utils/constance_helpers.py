# -*- coding: utf-8 -*-
"""
Хелперы для чтения настроек Constance.
Используются ключи, которые в dev-настройках хранятся как JSON-строка (список),
т.к. django-constance не поддерживает тип list в CONFIG.
"""
import json
from constance import config


def get_config_list(key):
    """
    Возвращает значение настройки Constance как список.
    Поддерживает: строку (JSON-массив), list/tuple (обратная совместимость), иначе [].
    """
    value = getattr(config, key, None)
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value or '[]')
            return list(parsed) if isinstance(parsed, (list, tuple)) else []
        except (TypeError, ValueError):
            return []
    return []


CONSTANCE_LIST_KEYS = (
    'DELIVERY_PICUP_PAYMENT_METHODS',
    'DELIVERY_TOADDRESS_PAYMENT_METHODS',
    'DELIVERY_TOTC_PAYMENT_METHODS',
    'DELIVERY_METHODS',
    'PAYMENT_METHODS',
    'DISPLAY_TAG_CONTAINERS',
)
