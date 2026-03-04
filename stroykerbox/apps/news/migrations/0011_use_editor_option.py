from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('news', '0010_news_updated_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='news',
            name='use_editor',
            field=models.BooleanField(default=True, verbose_name='использовать редактор'),
        ),
        migrations.AlterField(
            model_name='news',
            name='teaser',
            field=models.TextField(verbose_name='teaser text'),
        ),
        migrations.AlterField(
            model_name='news',
            name='text',
            field=models.TextField(verbose_name='text'),
        ),
    ]
