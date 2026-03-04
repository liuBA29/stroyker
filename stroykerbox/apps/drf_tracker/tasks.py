from django.core.management import call_command
from django_rq import job
from constance import config


@job('default')
def clear_api_logs() -> None:
    """
    Очистка БД от устаревших записей логов API.
    """
    if not config.API_TRACKER_ON:
        return

    days = getattr(config, 'API_TRACKER_LOG_LIFETIME_DAYS', 0)

    if days >= 0:
        call_command('clearapilogs', '--days_num', days)
