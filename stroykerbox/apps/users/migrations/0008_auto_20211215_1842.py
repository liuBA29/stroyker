from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_auto_20201013_1957'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='phone',
            field=models.CharField(
                help_text='Account phone number', max_length=18, verbose_name='phone'),
        ),
    ]
