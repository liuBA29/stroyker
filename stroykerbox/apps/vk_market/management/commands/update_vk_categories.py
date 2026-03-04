from django.core.management.base import BaseCommand
from django.utils.html import mark_safe

from stroykerbox.apps.vk_market.models import VKCategory
from stroykerbox.apps.vk_market.vk import VKMarket, vk_market_enabled, vk_settings_check


class Command(BaseCommand):

    def handle(self, *args, **options):
        verbosity = int(options['verbosity']) > 0

        if not vk_market_enabled():
            msg = None
            if verbosity:
                msg = ('В настоящее время VK-Маркет отлючен или не указаны все,'
                       ' необходимые для него, настройки.')
                msg += '<br />'
                msg += '<br />'.join(vk_settings_check())
            return mark_safe(msg)
        categories_dict = VKMarket().get_vk_categories()

        if isinstance(categories_dict, dict) and 'error' in categories_dict:
            return categories_dict['error'].get('error_msg') or 'Ошибка получения категорий'

        new = updated = 0
        if 'response' in categories_dict:
            for item in categories_dict['response']['items']:
                _, created = VKCategory.objects.update_or_create(
                    id=item['id'],
                    defaults={
                        'name': item['name'],
                        'section_id': item['section'].get('id', 0),
                        'section_name': item['section']['name']
                    }
                )
                if created:
                    new += 1
                else:
                    updated += 1
        if verbosity:
            return mark_safe(f'Создано: {new}<br />Обновлено: {updated}')
