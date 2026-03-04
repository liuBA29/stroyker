from typing import Optional
from logging import getLogger

from django.conf import settings
from django.core.management import call_command
from django.template.loader import get_template
from django.utils.functional import cached_property
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404
from django.contrib.sites.models import Site
from constance import config
from django_rq import job

from stroykerbox.settings.constants import INVOICING
from stroykerbox.apps.locations.models import Location
from stroykerbox.apps.telebot.helpers import telebot_is_active, telebot_send_message

from .models import Order
from .utils import invoice_pdf_is_allowed


mail_logger = getLogger('mail')

NEW_ORDER_DEFAULT_SUBJECT = 'Новый заказ в корзине'


class OrderNotify:

    def __init__(self, order_pk: int | str, **kwargs):
        self._order: Order = kwargs.get('instance') or get_object_or_404(
            Order, pk=order_pk
        )
        self.location: Optional[Location] = None
        if self._order.location and Location.objects.filter(is_active=True).count() > 1:
            self.location = self._order.location

    @cached_property
    def site_domain(self) -> str:
        site = Site.objects.get_current()
        return getattr(site, 'domain', '')

    @property
    def with_invoicing(self) -> bool:
        return all(
            (
                self._order.payment_method == INVOICING,
                invoice_pdf_is_allowed(self._order),
            )
        )

    @property
    def order_user(self):
        return self._order.user

    def get_notify_manager_emails(self) -> list:
        output = []

        # https://redmine.nastroyker.ru/issues/15631
        if self._order.user and self._order.user.personal_manager_email:
            output.append(self._order.user.personal_manager_email)
            if self._order.user.notify_personal_manager_only:
                return output

        if config.MANAGER_EMAILS:
            output += config.MANAGER_EMAILS.split(',')
        return output

    @property
    def order_user_email(self) -> Optional[str]:
        if self._order.user:
            return self._order.user.email
        elif hasattr(self._order, 'ordercontactdata'):
            return self._order.ordercontactdata.email
        return getattr(self._order.delivery, 'email', None)

    def order_notify_html(
        self, template: str, context_extra: Optional[dict] = None
    ) -> str:
        context = {
            'order': self._order,
            'location': self.location,
            'config': config,
            'contacts': (
                self._order.ordercontactdata
                if config.SIMPLE_CART_MODE
                else self._order.user
            ),
        }
        if context_extra:
            context.update(context_extra)
        return get_template(template).render(context)

    def order_notify_generate_invoice_pdf(self, template: str) -> bytes:
        from io import BytesIO
        from weasyprint import HTML, CSS

        html = self.order_notify_html(template)
        result = BytesIO()
        HTML(string=html).write_pdf(
            result, stylesheets=[CSS(settings.INVOICE_CSS_PATH)]
        )

        return result.getvalue()


@job('high')
def new_order_notify_customer(order_pk: int | str) -> str:
    """
    Send notification of a new order to the customer.
    """
    notify = OrderNotify(order_pk)
    if notify.order_user_email:
        subject = NEW_ORDER_DEFAULT_SUBJECT
        if notify.site_domain:
            subject += f' на сайте {notify.site_domain}'
        tpl = (
            'order-nofity-customer.html'
            if not config.SIMPLE_CART_MODE
            else 'order-nofity-customer-simple-mode.html'
        )
        context_extra = {'mail_header': subject}
        mail_body = notify.order_notify_html(
            f'cart/email/{tpl}', context_extra=context_extra
        )

        mail = EmailMessage(
            subject, mail_body, config.DEFAULT_FROM_EMAIL, [notify.order_user_email]
        )
        mail.content_subtype = 'html'
        if notify.with_invoicing:
            pdf = notify.order_notify_generate_invoice_pdf(
                'commerce/include/order-invoice-pdf.html'
            )
            mail.attach('invoice.pdf', pdf, 'application/pdf')
        try:
            mail.send(fail_silently=False)
        except Exception as e:
            mail_logger.exception(e)
            return 'FAILED'
        else:
            return 'OK'
    else:
        return 'No user email provided'


@job('high')
def new_order_notify_manager(order_pk: int | str) -> str:
    """
    Send notification of a new order to a manager.
    """
    notify = OrderNotify(order_pk)
    if manager_emails := notify.get_notify_manager_emails():
        subject = NEW_ORDER_DEFAULT_SUBJECT
        if notify.site_domain:
            subject += f' на сайте {notify.site_domain}'

        context_extra = {'mail_header': subject}

        mail_body = notify.order_notify_html(
            'cart/email/order-nofity-manager.html', context_extra=context_extra
        )

        mail = EmailMessage(
            subject,
            mail_body,
            config.DEFAULT_FROM_EMAIL,
            manager_emails,
        )
        mail.content_subtype = 'html'
        try:
            mail.send(fail_silently=False)
        except Exception as e:
            mail_logger.exception(e)
            return 'FAILED'
        else:
            return 'OK'
    else:
        return 'No manager emails provided'


def draft_order_notify_manager(order_pk: int | str) -> str:
    """
    Оповещение о "черновом" заказе.
    http://redmine.fancymedia.ru/issues/12917
    """
    try:
        order = Order.objects.get(pk=order_pk, status='draft')
    except Order.DoesNotExist:
        return f'Заказа с ID {order_pk} в статусе "черновика" не найдено.'

    if telebot_is_active() and config.TELEBOT_ORDER_FORM_ENABLED:
        if config.SIMPLE_CART_MODE:
            template = 'crm/telebot/draft-order-notification-simple-mode.html'
        else:
            template = 'crm/telebot/draft-order-notification.html'

        telebot_send_message(order, template)

    notify = OrderNotify(order.pk, instance=order)
    if manager_emails := notify.get_notify_manager_emails():
        subject = config.DRAFT_ORDER_NOFITY_EMAIL_SUBJECT
        if notify.site_domain:
            subject += f' на сайте {notify.site_domain}'

        context_extra = {'mail_header': subject}
        mail_body = notify.order_notify_html(
            'cart/email/draft-order-nofity-manager.html', context_extra=context_extra
        )

        mail = EmailMessage(
            subject,
            mail_body,
            config.DEFAULT_FROM_EMAIL,
            manager_emails,
        )
        mail.content_subtype = 'html'
        try:
            mail.send(fail_silently=False)
        except Exception as e:
            mail_logger.exception(e)
            return 'FAILED'
        else:
            return 'OK'
    else:
        return 'Не указаны email-адреса менеджеров для уведомлений. Почта не была отправлена.'


@job('default', timeout=1800)
def check_payment_yookassa() -> None:
    call_command('check_payment_yookassa')
