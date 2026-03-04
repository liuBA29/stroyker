from datetime import date, datetime

from django.utils.module_loading import import_string as import_module
from django import forms
from constance import config

from stroykerbox.apps.utils.forms import ReCaptchaFormMixin

from .fields import SelectField


class CFForm(ReCaptchaFormMixin, forms.Form):
    def __init__(self, custom_form_obj, *args, **kwargs):
        self.custom_form_obj = custom_form_obj
        super().__init__(*args, **kwargs)
        self.create_form_fields()

    def captcha_enabled(self):
        if super().captcha_enabled():
            return self.custom_form_obj.key in [f.strip() for f in config.RECAPTCHA_CUSTOM_FORMS.split(',')]

    def create_form_fields(self):
        for field in self.custom_form_obj.fields.all():
            field_class = import_module(field.field_class)

            kwargs = {}
            if field_class is SelectField:
                kwargs['key'] = field.html_name

            self.fields[field.html_name] = field_class(
                label=field.label if field.show_label else '',
                required=field.required, **kwargs
            )

            if field.css_classes:
                classes = self.fields[field.html_name].widget.attrs.get(
                    'class', '')
                if classes:
                    classes += ' '
                classes += field.css_classes

                self.fields[field.html_name].widget.attrs['class'] = classes
            if field.placeholder:
                self.fields[field.html_name].widget.attrs['placeholder'] = field.placeholder

    def clean(self):
        data = self.cleaned_data
        for k, v in data.items():
            if isinstance(v, (datetime, date)):
                data[k] = v.isoformat()
        return data
