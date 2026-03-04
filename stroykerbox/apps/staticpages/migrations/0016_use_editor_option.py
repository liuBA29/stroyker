from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('staticpages', '0015_position_for_file_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='page',
            name='use_editor',
            field=models.BooleanField(default=True, verbose_name='использовать редактор'),
        ),
        migrations.AlterField(
            model_name='page',
            name='text',
            field=models.TextField(blank=True, help_text='HTML content of the page if it is static', null=True, verbose_name='text'),
        ),
    ]
