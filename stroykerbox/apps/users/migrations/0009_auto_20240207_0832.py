from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_auto_20211215_1842'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='calculation',
            field=models.CharField(choices=[('discount', 'скидка на цену'), (
                'extra_charge', 'наценка на закупочную цену')], default='discount', max_length=32, verbose_name='Вариант расчета'),
        ),
        migrations.RenameField(
            model_name='user',
            old_name='personal_discount',
            new_name='discount'
        ),
        migrations.AddField(
            model_name='userdiscountgroup',
            name='calculation',
            field=models.CharField(choices=[('discount', 'скидка на цену'), (
                'extra_charge', 'наценка на закупочную цену')], default='discount', max_length=32, verbose_name='Вариант расчета'),
        ),
        migrations.AlterField(
            model_name='user',
            name='discount',
            field=models.SmallIntegerField(default=0, verbose_name='Процент'),
        ),
    ]
