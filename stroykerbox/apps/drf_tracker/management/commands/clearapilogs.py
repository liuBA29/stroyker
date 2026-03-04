import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from stroykerbox.apps.drf_tracker.models import APIRequestLog


class Command(BaseCommand):
    help = 'Удаление из базы данных записей логов API.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days_num',
            help='Сохранить последние данные за указанное кол-во дней.',
            type=int,
        )

    def handle(self, *args, **options):
        days_num = options['days_num']

        if days_num:
            today = timezone.now()
            start_date = today - datetime.timedelta(days=days_num)
            logs_to_delete = APIRequestLog.objects.filter(requested_at__lt=start_date)

        else:
            logs_to_delete = APIRequestLog.objects.all()

        deleted_logs_count = logs_to_delete.count()
        logs_to_delete.delete()

        if deleted_logs_count:
            success_message = f'Удалено логов: {deleted_logs_count}'
        else:
            success_message = 'Логов для удаления не найдено'

        self.stdout.write(self.style.SUCCESS(success_message))
