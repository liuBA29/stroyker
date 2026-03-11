# Generated manually for new design tag containers

from django.db import migrations


NEW_DESIGN_CONTAINERS = [
    ('new_design_middle', 'Новый дизайн: блоки главной страницы'),
    ('new_design_bottom', 'Новый дизайн: блоки футера'),
]


def create_new_design_containers(apps, schema_editor):
    SliderTagContainer = apps.get_model('customization', 'SliderTagContainer')
    for key, name in NEW_DESIGN_CONTAINERS:
        SliderTagContainer.objects.get_or_create(
            key=key,
            defaults={'name': name}
        )


def remove_new_design_containers(apps, schema_editor):
    SliderTagContainer = apps.get_model('customization', 'SliderTagContainer')
    SliderTagContainer.objects.filter(
        key__in=[k for k, _ in NEW_DESIGN_CONTAINERS]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('customization', '0064_remove_mobilemenubutton_type_additional_menu'),
    ]

    operations = [
        migrations.RunPython(create_new_design_containers, remove_new_design_containers),
    ]
