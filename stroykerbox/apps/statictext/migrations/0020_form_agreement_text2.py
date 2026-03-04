from django.db import migrations

KEY = 'form_agreement_text2'


def create_new(app, *args, **kwargs):
    """
    https://redmine.nastroyker.ru/issues/19357
    """
    app.get_model('statictext', 'Statictext').objects.get_or_create(
        key=KEY,
        defaults=dict(
            text='',
            comment='Текст для второго чекбокса "соглашения".',
        ),
    )


class Migration(migrations.Migration):

    dependencies = [
        ('statictext', '0019_partners_become_partner_btn'),
    ]

    operations = [
        migrations.RunPython(create_new, reverse_code=migrations.RunPython.noop)
    ]
