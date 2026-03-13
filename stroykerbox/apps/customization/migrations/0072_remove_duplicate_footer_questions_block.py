# Удаляем дубликаты блока «Остались вопросы?» в контейнере футера — оставляем один (с минимальной позицией).

from django.db import migrations

QUESTIONS_TAG = 'customization_tags:render_new_design_footer_questions_block'


def remove_duplicate_questions_blocks(apps, schema_editor):
    SliderTagContainer = apps.get_model('customization', 'SliderTagContainer')
    SliderTagContainerItem = apps.get_model('customization', 'SliderTagContainerItem')
    try:
        container = SliderTagContainer.objects.get(key='new_design_footer')
    except SliderTagContainer.DoesNotExist:
        return

    items = list(
        SliderTagContainerItem.objects.filter(
            container=container,
            tag_line=QUESTIONS_TAG,
        ).order_by('position')
    )
    if len(items) <= 1:
        return
    # Оставляем первый (с минимальной позицией), остальные удаляем
    for item in items[1:]:
        item.delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('customization', '0071_remove_footer_tags_from_body_containers'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_questions_blocks, noop),
    ]
