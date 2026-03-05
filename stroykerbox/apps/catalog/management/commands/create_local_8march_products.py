# -*- coding: utf-8 -*-
"""
Создать рандомные тестовые товары в локальную БД для проверки блока «Акции» на /8march_design/.
Только для разработки; не запускать на проде с боевой базой.
"""
import random

from django.core.management.base import BaseCommand
from model_bakery import baker

from stroykerbox.apps.catalog.models import Category, Product


class Command(BaseCommand):
    help = 'Создать тестовые товары (рандомные названия и цены) для локальной разработки 8march.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=24,
            help='Сколько товаров создать (по умолчанию 24).',
        )

    def handle(self, *args, **options):
        count = options['count']
        if count < 1:
            self.stdout.write(self.style.WARNING('count должен быть >= 1.'))
            return

        # Берём первую попавшуюся корневую категорию или создаём одну тестовую.
        root = Category.objects.filter(level=0, published=True).first()
        if not root:
            root = Category.objects.create(
                name='Тестовая категория',
                slug='testovaya-kategoriya',
                parent=None,
                published=True,
            )
            self.stdout.write(f'Создана категория: {root.name} (slug={root.slug})')

        names = [
            'Букет из роз',
            'Букет из тюльпанов',
            'Букет из пионов',
            'Букет из гортензий',
            'Моно букет из гербер',
            'Композиция из полевых цветов',
            'Букет с эвкалиптом',
            'Свадебный букет',
            'Букет на 8 марта',
            'Авторский букет',
            'Букет в коробке',
            'Мини-букет',
        ]

        created = 0
        for i in range(count):
            name = random.choice(names) + f' #{i + 1}'
            slug = f'test-product-8march-{i + 1}'
            sku = f'LOCAL8M{i + 1:04d}'
            price = random.randint(1200, 5500)
            if random.random() > 0.5:
                old_price = price + random.randint(200, 800)
            else:
                old_price = None

            if Product.objects.filter(slug=slug).exists():
                continue
            product = baker.make(
                Product,
                name=name,
                slug=slug,
                sku=sku,
                published=True,
                price=price,
                old_price=old_price,
            )
            product.categories.add(root)
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Создано товаров: {created}. Категория: {root.name}'))
