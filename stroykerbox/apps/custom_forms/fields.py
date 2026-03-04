from django.forms import (CharField, Textarea, DateField as OriginalDateField, DateInput, MultipleHiddenInput,
                          FileField as OriginalFileField, ModelChoiceField)

from .models import CustomSelectFieldChoiceModel
from .validators import phone_validator


class PhoneField(CharField):
    default_validators = [phone_validator]

    def __init__(self, **kwargs):
        super().__init__(strip=True, **kwargs)

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs['class'] = 'phone'
        return attrs


class TextareaField(CharField):
    widget = Textarea

    def __init__(self, **kwargs):
        super().__init__(strip=True, **kwargs)


class DateInputCustom(DateInput):
    input_type = 'date'


class DateField(OriginalDateField):
    widget = DateInputCustom


class FileField(OriginalFileField):
    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs['multiple'] = True
        return attrs


class PseudoFileInput(MultipleHiddenInput):
    template_name = 'custom_forms/pseudo_file.html'


class PseudoFileField(CharField):
    widget = PseudoFileInput

    def to_python(self, values):
        """Return a string."""
        if isinstance(values, list):
            values = [v.strip() for v in values if v.strip()]
            if values:
                return values
        return super().to_python(values)


class SelectField(ModelChoiceField):
    def __init__(self, *args, **kwargs):
        key = kwargs.pop('key')
        queryset = CustomSelectFieldChoiceModel.objects.filter(field__key=key)
        if 'empty_label' not in kwargs and kwargs.get('required'):
            kwargs['empty_label'] = None
        super().__init__(queryset, *args, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        return str(value) if value else ''
