# Убираем футерные теги из контейнеров тела страницы (middle/bottom),
# чтобы «Остались вопросы?» и блоки меню/копирайт были только в футере (одна рубрика вопросов).

from django.db import migrations

FOOTER_TAG_LINES = [
    'customization_tags:render_new_design_footer_questions_block',
    'customization_tags:render_new_design_footer_menu_block',
    'customization_tags:render_new_design_footer_copyright_block',
]


def remove_footer_tags_from_body_containers(apps, schema_editor):
    SliderTagContainer = apps.get_model('customization', 'SliderTagContainer')
    SliderTagContainerItem = apps.get_model('customization', 'SliderTagContainerItem')
    for key in ('new_design_middle', 'new_design_bottom'):
        try:
            container = SliderTagContainer.objects.get(key=key)
        except SliderTagContainer.DoesNotExist:
            continue
        SliderTagContainerItem.objects.filter(
            container=container,
            tag_line__in=FOOTER_TAG_LINES,
        ).delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('customization', '0070_new_design_footer_default_items'),
    ]

    operations = [
        migrations.RunPython(remove_footer_tags_from_body_containers, noop),
    ]
