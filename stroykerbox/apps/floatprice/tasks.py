from logging import getLogger

from django.core.management import call_command
from constance import config
import django_rq

from .models import FloatPrice

logger = getLogger(__name__)

UPDATE_TASK = 'stroykerbox.apps.floatprice.tasks.update_floatprices'


def delete_float_prices() -> str:
    """
    Удаление объектов "плавающий цен" про деактивации оных в настройках.
    https://redmine.nastroyker.ru/issues/14970
    """
    result, __ = FloatPrice.objects.all().delete()
    return f'Удалено "плавающих цен": {result}'


def set_floatprice_job():
    minute = config.FLOATPRICE_UPD_TIME.minute
    hour = config.FLOATPRICE_UPD_TIME.hour
    days = '*'
    if config.FLOATPRICE_UPD_DAYS > 0:
        days += f'/{config.FLOATPRICE_UPD_DAYS}'
    cron_string = f'{minute} {hour} {days} * *'

    job = None

    try:
        scheduler = django_rq.get_scheduler()
        job = scheduler.cron(cron_string, UPDATE_TASK)
    except Exception as e:
        logger.exception(e)

    return job


def check_floatprice_task_on_startup():
    """
    Проверка существования таска и его запуск при старте инстанса проекта, если
    функционал включен.
    """
    try:
        scheduler = django_rq.get_scheduler()
        for job in scheduler.get_jobs():
            if job.func.__name__ == UPDATE_TASK.split('.')[-1]:
                return

        if all((config.FLOATPRICE_IS_ACTIVE, config.FLOATPRICE_PERCENT > 0)):
            return set_floatprice_job()
    except Exception as e:
        logger.exception(e)


def update_floatprice_task(run_new=True):
    """
    Обновление таска при изменении настроек.
    """
    try:
        scheduler = django_rq.get_scheduler()
        for job in scheduler.get_jobs():
            if job.func.__name__ == UPDATE_TASK.split('.')[-1]:
                job.delete()
        if run_new and all(
            (config.FLOATPRICE_IS_ACTIVE, config.FLOATPRICE_PERCENT > 0)
        ):
            return set_floatprice_job()
        else:
            return delete_float_prices()
    except Exception as e:
        logger.exception(e)


@django_rq.job('default', timeout=1800)
def update_floatprices():
    """
    Запуск обновления "плавающих цен" ассинхронно, отдельным таском.
    """
    call_command('update_floatprices', '--verbosity=0')


# def test_func():
#     scheduler = django_rq.get_scheduler()
#     jobs = [job for job in scheduler.get_jobs()]
