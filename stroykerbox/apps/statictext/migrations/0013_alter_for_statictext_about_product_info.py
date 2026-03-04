from django.db import migrations


def change_statictext(app, schema):
    Statictext = app.get_model('statictext', 'Statictext')
    try:
        obj = Statictext.objects.get(key='text_about_payment_on_product_page')
    except Statictext.DoesNotExist:
        return

    obj.text = ''
    obj.save()


class Migration(migrations.Migration):

    dependencies = [
        ('statictext', '0012_text_about_payment_on_product_page'),
    ]

    operations = [
        migrations.RunPython(change_statictext, migrations.RunPython.noop),
    ]
