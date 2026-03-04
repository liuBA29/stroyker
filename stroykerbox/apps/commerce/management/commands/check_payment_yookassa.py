from logging import getLogger

from constance import config
from django.core.management.base import BaseCommand

from stroykerbox.apps.commerce import utils, tasks
from stroykerbox.apps.commerce.models import Order
from stroykerbox.apps.commerce.payment import yookassa_payment
from stroykerbox.settings.constants import YOOKASSA

logger = getLogger('yml_export')


class Command(BaseCommand):
    help = 'Check orders for payment yookassa'

    def handle(self, *args, **options):
        orders = Order.objects.filter(
            payment_method=YOOKASSA,
            is_paid=False,
            yookassa_status__in=(Order.YOOKASSA_PENDING, Order.WAITING_FOR_CAPTURE)
        )
        for order in tuple(orders):
            yookassa_payment.check_status(order)
            if order.yookassa_status == Order.YOOKASSA_SUCCEEDED:
                old_status = order.status
                order.is_paid = True
                order.status = 'new'
                order.save()

                if order.from_cart and old_status == 'draft':
                    tasks.new_order_notify_customer.delay(order.pk)

                if config.WHITETHEME_SHOW_LK_LINKS and not hasattr(order, 'user'):
                    utils.new_customer_order_registration(order)

                tasks.new_order_notify_manager.delay(order.pk)
