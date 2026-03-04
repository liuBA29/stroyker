from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('custom_forms', '0008_auto_20240415_1451'),
    ]

    operations = [
        migrations.AddField(
            model_name='customformfield',
            name='b24_alias',
            field=models.CharField(blank=True, choices=[('NAME', 'NAME'), ('PHONE', 'PHONE'), ('EMAIL', 'EMAIL'), (
                'COMMENTS', 'COMMENTS')], help_text='Альяс(сопоставление) поля для Bitrix24', max_length=32, null=True, verbose_name='поле в b24'),
        ),
        migrations.AlterField(
            model_name='customformfield',
            name='field_class',
            field=models.CharField(choices=[('django.forms.FloatField', 'float'), ('django.forms.CharField', 'text string'), ('stroykerbox.apps.custom_forms.fields.PhoneField', 'phone'), ('stroykerbox.apps.custom_forms.fields.PseudoFileField', 'multiple files with preload'), ('django.forms.EmailField', 'email'), ('stroykerbox.apps.custom_forms.fields.SelectField', 'select field'), ('django.forms.URLField', 'url'), (
                'django.forms.BooleanField', 'boolean'), ('django.forms.IntegerField', 'integer'), ('django.forms.FileField', 'file'), ('stroykerbox.apps.custom_forms.fields.DateField', 'date'), ('stroykerbox.apps.custom_forms.fields.FileField', 'multiple files'), ('stroykerbox.apps.custom_forms.fields.TextareaField', 'multiline text')], max_length=128, verbose_name='form field class'),
        ),
    ]
