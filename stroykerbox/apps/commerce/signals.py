from django import dispatch
from django.dispatch import receiver
from django.core.management import call_command
from django.utils import timezone
from django.db.models.signals import post_save
from constance.signals import config_updated
from constance import config
import django_rq

from .utils import update_yookassa_connect
from .models import Order
from .tasks import draft_order_notify_manager

new_order_created = dispatch.Signal(providing_args=['order'])
order_paid_by_yookassa = dispatch.Signal(providing_args=['order'])


@receiver(config_updated)
def constance_updated(sender, key, old_value, new_value, **kwargs):
    if (old_value == '' and new_value is None) or (old_value == new_value):
        return

    if key in {'YOOKASSA_ACCOUNT_ID', 'YOOKASSA_SECRET_KEY'}:
        secret_key = new_value if key == 'YOOKASSA_SECRET_KEY' else None
        account_id = new_value if key == 'YOOKASSA_ACCOUNT_ID' else None
        update_yookassa_connect(account_id, secret_key)
    elif key == 'YOOKASSA_CHECK_ORDER_PERIOD':
        call_command('payment_sync_scheduler')


@receiver(post_save, sender=Order)
def new_draft_order(sender, instance, created, **kwargs):
    if not all(
        (
            created,
            instance.status == 'draft',
            config.DRAFT_ORDER_NOFITY_ON,
            config.DRAFT_ORDER_NOFITY_TIMEOUT_SEC > 0,
        )
    ):
        return

    run_time = timezone.now() + timezone.timedelta(
        seconds=config.DRAFT_ORDER_NOFITY_TIMEOUT_SEC
    )
    scheduler = django_rq.get_scheduler()
    scheduler.enqueue_at(run_time, draft_order_notify_manager, instance.pk)
