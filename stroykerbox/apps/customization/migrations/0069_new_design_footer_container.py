# Контейнер new_design_footer: блоки футера (меню, копирайт, «Остались вопросы?»)

from django.db import migrations


def add_new_design_footer_container(apps, schema_editor):
    SliderTagContainer = apps.get_model('customization', 'SliderTagContainer')
    SliderTagContainer.objects.get_or_create(
        key='new_design_footer',
        defaults={'name': 'Новый дизайн: футер (теги)'}
    )


def remove_new_design_footer_container(apps, schema_editor):
    SliderTagContainer = apps.get_model('customization', 'SliderTagContainer')
    SliderTagContainer.objects.filter(key='new_design_footer').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('customization', '0068_slidertagcontaineritem_preview_image'),
    ]

    operations = [
        migrations.RunPython(add_new_design_footer_container, remove_new_design_footer_container),
    ]

