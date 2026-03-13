# Дефолтные блоки футера в контейнере new_design_footer

from django.db import migrations


DEFAULT_ITEMS = [
    # Показываем только на главной (не на /8march_design/)
    ('customization_tags:render_new_design_footer_questions_block', 0, True),
    ('customization_tags:render_new_design_footer_menu_block', 10, False),
    ('customization_tags:render_new_design_footer_copyright_block', 20, False),
]


def add_default_items(apps, schema_editor):
    SliderTagContainer = apps.get_model('customization', 'SliderTagContainer')
    SliderTagContainerItem = apps.get_model('customization', 'SliderTagContainerItem')
    try:
        container = SliderTagContainer.objects.get(key='new_design_footer')
    except SliderTagContainer.DoesNotExist:
        return

    for tag_line, position, frontpage_only in DEFAULT_ITEMS:
        SliderTagContainerItem.objects.get_or_create(
            container=container,
            tag_line=tag_line,
            defaults={
                'position': position,
                'enabled': True,
                'without_wrapper': True,
                'frontpage_only': frontpage_only,
            }
        )


def remove_default_items(apps, schema_editor):
    SliderTagContainer = apps.get_model('customization', 'SliderTagContainer')
    SliderTagContainerItem = apps.get_model('customization', 'SliderTagContainerItem')
    try:
        container = SliderTagContainer.objects.get(key='new_design_footer')
    except SliderTagContainer.DoesNotExist:
        return

    tag_lines = [t for t, _, _ in DEFAULT_ITEMS]
    SliderTagContainerItem.objects.filter(container=container, tag_line__in=tag_lines).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('customization', '0069_new_design_footer_container'),
    ]

    operations = [
        migrations.RunPython(add_default_items, remove_default_items),
    ]

