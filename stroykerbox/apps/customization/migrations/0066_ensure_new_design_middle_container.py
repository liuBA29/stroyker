# Восстановление контейнера «Новый дизайн: блоки главной страницы», если был удалён из админки

from django.db import migrations


NEW_DESIGN_CONTAINERS = [
    ('new_design_middle', 'Новый дизайн: блоки главной страницы'),
    ('new_design_bottom', 'Новый дизайн: блоки футера'),
]


def ensure_new_design_containers(apps, schema_editor):
    SliderTagContainer = apps.get_model('customization', 'SliderTagContainer')
    for key, name in NEW_DESIGN_CONTAINERS:
        SliderTagContainer.objects.get_or_create(
            key=key,
            defaults={'name': name}
        )


class Migration(migrations.Migration):

    dependencies = [
        ('customization', '0065_new_design_tag_containers'),
    ]

    operations = [
        migrations.RunPython(ensure_new_design_containers, migrations.RunPython.noop),
    ]
