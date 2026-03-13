# -*- coding: utf-8 -*-
"""
Устанавливает DISPLAY_TAG_CONTAINERS для локальной разработки без сохранения через админку.
Использование: python manage.py set_display_tag_containers
(в админке при сохранении Constance в dev может возникать "signal only works in main thread").
"""
from django.core.management.base import BaseCommand
from constance import config


class Command(BaseCommand):
    help = 'Set DISPLAY_TAG_CONTAINERS (middle, bottom + new design containers) for local test'

    def handle(self, *args, **options):
        value = '["middle", "bottom", "new_design_middle", "new_design_bottom", "new_design_footer"]'
        config.DISPLAY_TAG_CONTAINERS = value
        self.stdout.write(
            self.style.SUCCESS('DISPLAY_TAG_CONTAINERS = %s' % value)
        )
