from django.dispatch import receiver
from constance.signals import config_updated

from . import tasks


@receiver(config_updated)
def process_floatprice_config(sender, key, old_value, new_value, **kwargs):
    if key == 'FLOATPRICE_IS_ACTIVE':
        if old_value == new_value:
            return

        if new_value:
            tasks.update_floatprices.delay()
            tasks.update_floatprice_task()
        else:
            tasks.update_floatprice_task(run_new=False)
