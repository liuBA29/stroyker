# Добавление поля «Превью (админка)» для картинки блока в контейнерах new_design

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customization', '0067_new_design_after_wish_container'),
    ]

    operations = [
        migrations.AddField(
            model_name='slidertagcontaineritem',
            name='preview_image',
            field=models.ImageField(
                blank=True,
                help_text='Optional: image for this block in the admin (new_design only).',
                null=True,
                upload_to='customization/admin_tag_previews/',
                verbose_name='preview image (admin)',
            ),
        ),
    ]
