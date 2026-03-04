from typing import Optional

from stroykerbox.apps.users.models import User
from stroykerbox.apps.users.tasks import new_registration_notify_manager
from yookassa import Configuration

from constance import config
from stroykerbox.settings.constants import (
    BILLING_CONF_ITEMS,
    INVOICING,
    CARD_UPON_RECEIPT,
    CASH_UPON_RECEIPT,
    ONLINE_ON_SITE,
    CREDIT,
    YOOKASSA,
)


def get_payment_methods_names(as_dict=True):
    names = (
        (INVOICING, config.INVOICING_DISPLAY_NAME),
        (CARD_UPON_RECEIPT, config.CARD_UPON_RECEIPT_DISPLAY_NAME),
        (CASH_UPON_RECEIPT, config.CASH_UPON_RECEIPT_DISPLAY_NAME),
        (ONLINE_ON_SITE, config.ONLINE_ON_SITE_DISPLAY_NAME),
        (CREDIT, config.CREDIT_DISPLAY_NAME),
        (YOOKASSA, config.YOOKASSA_DISPLAY_NAME),
    )
    if as_dict:
        return dict(names)
    return names


def new_customer_order_registration(order, is_active=False):
    account = User.objects.create_user(
        email=order.delivery.email,
        name=order.delivery.name,
        phone=order.delivery.phone,
        is_active=is_active,
    )
    if not is_active:
        new_registration_notify_manager.delay(account)


def invoice_pdf_is_allowed(order):
    """
    Check that exist all the necessary payment details of the recipient and of the customer.
    """
    if not config.INVOICE_PDF_AUTOGENERATION:
        return False
    elif not order.user and not config.INVOICE_PDF_ANON_ALLOWED:
        return False

    for item in BILLING_CONF_ITEMS:
        if item in ('BILLING_INFO__VAT', 'BILLING_INFO__SIGNATURE_FILE'):
            continue
        if not getattr(config, item, False):
            return False

    return True


def update_yookassa_connect(
    account_id: Optional[str] = None, secret_key: Optional[str] = None
) -> None:
    account_id = account_id or getattr(config, 'YOOKASSA_ACCOUNT_ID', '')
    secret_key = secret_key or getattr(config, 'YOOKASSA_SECRET_KEY', '')
    Configuration.configure(account_id, secret_key)
