from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('seo', '0003_auto_20230120_1455'),
    ]

    operations = [
        migrations.AddField(
            model_name='metatag',
            name='ai_keywords',
            field=models.TextField(blank=True, default='', help_text='Ключевые слова для ИИ.'),
        ),
    ]
