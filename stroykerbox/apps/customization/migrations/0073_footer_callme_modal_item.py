# Добавляем в футер 8 марта отдельный пункт контейнера — модалка «ПЕРЕЗВОНИТЕ МНЕ».
# Рендерится отдельно от блока «Остались вопросы», чтобы при сбое модалки блок не пропадал.

from django.db import migrations


CALLME_MODAL_TAG = 'customization_tags:render_new_design_footer_callme_modal'


def add_callme_modal_item(apps, schema_editor):
    SliderTagContainer = apps.get_model('customization', 'SliderTagContainer')
    SliderTagContainerItem = apps.get_model('customization', 'SliderTagContainerItem')
    try:
        container = SliderTagContainer.objects.get(key='new_design_footer')
    except SliderTagContainer.DoesNotExist:
        return

    SliderTagContainerItem.objects.get_or_create(
        container=container,
        tag_line=CALLME_MODAL_TAG,
        defaults={
            'position': 5,
            'enabled': True,
            'without_wrapper': True,
            'frontpage_only': False,
        }
    )


def remove_callme_modal_item(apps, schema_editor):
    SliderTagContainer = apps.get_model('customization', 'SliderTagContainer')
    SliderTagContainerItem = apps.get_model('customization', 'SliderTagContainerItem')
    try:
        container = SliderTagContainer.objects.get(key='new_design_footer')
    except SliderTagContainer.DoesNotExist:
        return

    SliderTagContainerItem.objects.filter(
        container=container,
        tag_line=CALLME_MODAL_TAG,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('customization', '0072_remove_duplicate_footer_questions_block'),
    ]

    operations = [
        migrations.RunPython(add_callme_modal_item, remove_callme_modal_item),
    ]
