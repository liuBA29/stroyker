from django.core.management.base import BaseCommand

from stroykerbox.apps.smartlombard.tbank.models import TBankPayment


class Command(BaseCommand):
    help = (
        'Обновление данных о платежах через Т-Банк. '
        'Проверка производиться только для платежей со статусом "NEW".'
    )

    def handle(self, *args, **options):
        for payment in TBankPayment.objects.filter(status='NEW'):
            if payment.update_payment_status():
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Успешно обновлены данные для платежа {payment.pk}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Ошибки при обновлении платежа {payment.pk}')
                )
