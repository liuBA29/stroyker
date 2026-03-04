import django.contrib.postgres.fields.ranges
import django.contrib.postgres.validators
from django.db import migrations, models
import django.db.models.deletion


def migrate_ranges(apps, *args, **kwargs):
    ItemSetHourRange = apps.get_model('booking', 'ItemSetHourRange')
    for i in apps.get_model('booking', 'ItemSet').objects.filter(hours_range__isnull=False):
        ItemSetHourRange.objects.create(itemset=i, hours_range=i.hours_range)


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0002_auto_20240312_1635'),
    ]

    operations = [
        migrations.CreateModel(
            name='ItemSetHourRange',
            fields=[
                ('id', models.BigAutoField(auto_created=True,
                 primary_key=True, serialize=False, verbose_name='ID')),
                ('hours_range', django.contrib.postgres.fields.ranges.IntegerRangeField(validators=[django.contrib.postgres.validators.RangeMinValueValidator(
                    0), django.contrib.postgres.validators.RangeMaxValueValidator(23)], verbose_name='диапазон часов')),
                ('itemset', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                 related_name='hour_ranges', to='booking.itemset', verbose_name='набор')),
            ],
            options={
                'verbose_name': 'диапазон часов для наборов слотов брони',
                'verbose_name_plural': 'диапазоны часов для наборов слотов брони',
            },
        ),
        migrations.RunPython(migrate_ranges, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='itemset',
            name='hours_range',
        ),
    ]
