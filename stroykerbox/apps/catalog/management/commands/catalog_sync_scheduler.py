#  https://gist.github.com/LucasRoesler/9574647
# https://github.com/rq/rq-scheduler/issues/51#issuecomment-536652049

from datetime import datetime, timedelta
import logging

from django.conf import settings
from constance import config
import django_rq
from django_rq.management.commands import rqscheduler

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
        func_names = [j['task'] for j in settings.RQ_PERIODIC]
        for j in scheduler.get_jobs():
            if j.func_name in func_names:
                scheduler.cancel(j)

        for task in settings.RQ_PERIODIC:
            # grab the function path, remove it from the dictionary
            t = task.pop('task')
            task_name = t.split('.')[-1]

            if task_name == 'sync_moy_sklad_prices':
                scheduled_time = datetime.utcnow() + timedelta(minutes=5)
                interval = int(config.SYNC_PRICES_PERIOD)
            elif task_name == 'sync_moy_sklad_stocks':
                scheduled_time = datetime.utcnow() + timedelta(minutes=15)
                interval = int(config.SYNC_STOCKS_PERIOD)
            elif task_name == 'update_yml_file':
                scheduled_time = datetime.utcnow() + timedelta(minutes=1)
                interval = int(config.YML_UPDATE_INTERVAL)
            elif task_name == 'update_novofon_stats':
                scheduled_time = datetime.utcnow() + timedelta(minutes=1)
                interval = int(config.NOVOFON_UPDATE_INTERVAL)
            else:
                scheduled_time = datetime.utcnow()
                interval = int(task.get('interval', 4))

            interval = int(interval) * 3600 if interval > 0 else 4 * 3600

            scheduler.schedule(
                scheduled_time=scheduled_time,  # Time for first execution, in UTC timezone
                func=import_function(t),  # Function to be queued
                args=[],  # Arguments passed into function when executed
                kwargs={},  # Keyword arguments passed into function when executed
                # Function calling interval, in seconds
                interval=interval,
                # Repeat this number of times (None means repeat forever)
                repeat=None,
                meta={},  # Arbitrary pickleable data on the job itself
            )
            logger.debug(f'Task {t} added to scheduler.')

        # verbose logging
        s = [t.func_name for t in scheduler.get_jobs()]
        logger.info(
            'Currently scheduled catalog sync tasks ({}):\n {}'.format(
                len(s), '\n '.join(s)
            )
        )

        super().handle(*args, **options)
