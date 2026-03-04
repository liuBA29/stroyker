from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db.models.functions import Lower

UserModel = get_user_model()


class Command(BaseCommand):

    help = 'Массовое приведение пользовательских email-адресов к нижнему регистру.'

    def handle(self, *args, **options):
        try:
            update_result = UserModel.objects.update(email=Lower('email'))
        except Exception as e:
            self.stderr(str(e))
        else:
            self.stdout.write(f'Обновлено email-адресов: {update_result}')
