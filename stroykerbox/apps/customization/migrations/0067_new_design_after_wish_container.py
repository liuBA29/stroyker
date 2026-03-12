# Контейнер «после блока Букет по желаниям» — блоки между «Букет по вашим желаниям» и «Отзывы»

from django.db import migrations


def add_after_wish_container(apps, schema_editor):
    SliderTagContainer = apps.get_model('customization', 'SliderTagContainer')
    SliderTagContainer.objects.get_or_create(
        key='new_design_after_wish',
        defaults={'name': 'Новый дизайн: после блока «Букет по желаниям»'}
    )


class Migration(migrations.Migration):

    dependencies = [
        ('customization', '0066_ensure_new_design_middle_container'),
    ]

    operations = [
        migrations.RunPython(add_after_wish_container, migrations.RunPython.noop),
    ]
