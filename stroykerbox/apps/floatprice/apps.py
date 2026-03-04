from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class FloatpriceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stroykerbox.apps.floatprice'
    verbose_name = _('Плавающая цена')

    def ready(self):
        from . import signals  # noqa
        from .tasks import check_floatprice_task_on_startup

        # На случай перезагрузки инстанса проекта - перезапускаем таск обновления
        # плавающих цен, если оно включено в настройках.
        check_floatprice_task_on_startup()
