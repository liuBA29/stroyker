#  https://gist.github.com/LucasRoesler/9574647
# https://github.com/rq/rq-scheduler/issues/51#issuecomment-536652049

from datetime import datetime
import logging

from django.conf import settings
import django_rq
from django_rq.management.commands import rqscheduler
from constance import config

from stroykerbox.apps.utils.utils import import_function, clear_scheduled_jobs

logger = logging.getLogger('rq_scheduler')

scheduler = django_rq.get_scheduler()


class Command(rqscheduler.Command):
    """
    Schedules (reschedules) catalog-MoySklad synchronization tasks.
    """

    def handle(self, *args, **options):
        clear_scheduled_jobs(scheduler, logger)

        # cancel any currently scheduled tasks that are listed in the
        # settings.
        func_names = [j['task'] for j in settings.RQ_PERIODIC_PAYMENT]
        for j in scheduler.get_jobs():
            if j.func_name in func_names:
                scheduler.cancel(j)

        for task in settings.RQ_PERIODIC_PAYMENT:
            scheduler.schedule(
                scheduled_time=datetime.utcnow(),  # Time for first execution, in UTC timezone
                func=import_function(task['task']),  # Function to be queued
                args=task['args'],  # Arguments passed into function when executed
                kwargs=task['kwargs'],  # Keyword arguments passed into function when executed
                # Function calling interval, in seconds
                interval=config.YOOKASSA_CHECK_ORDER_PERIOD,
                # Repeat this number of times (None means repeat forever)
                repeat=None,
                meta={}  # Arbitrary pickleable data on the job itself
            )
        super().handle(*args, **options)
