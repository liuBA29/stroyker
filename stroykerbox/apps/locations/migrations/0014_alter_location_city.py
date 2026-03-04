from django.db import migrations, models
import django.db.models.deletion


def set_coords(apps, *args, **kwargs):
    Location = apps.get_model('locations.Location')

    for i in Location.objects.filter(
        (models.Q(latitude__isnull=True) | models.Q(longitude__isnull=True)),
        city__isnull=False,
    ):
        if not i.latitude:
            i.latitude = i.city.latitude
        if not i.longitude:
            i.longitude = i.city.longitude
        i.save(update_fields=('longitude', 'latitude'))


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0013_location_email'),
    ]

    operations = [
        migrations.RunPython(set_coords, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name='location',
            name='city',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='location',
                to='django_geoip.city',
            ),
        ),
    ]
