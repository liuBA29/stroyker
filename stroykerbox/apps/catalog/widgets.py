from django import forms
from django.utils.html import format_html
from django.utils.translation import ugettext as _


class MultiChoiceFilterWidget(forms.widgets.CheckboxSelectMultiple):
    option_template_name = 'catalog/widgets/checkbox.html'
    template_name = 'catalog/widgets/multiple_input.html'


class CustomCheckboxChoiceInput(forms.widgets.CheckboxInput):
    def render(self, name=None, value=None, attrs=None, choices=()):
        if 'class' not in self.attrs:
            self.attrs['class'] = 'checkbox'

        if self.id_for_label:
            label_for = format_html(' for="{0}"', self.id_for_label)
        else:
            label_for = ''
        return format_html('<label{0}>{1} <span>{2}</span></label>', label_for, self.tag(), self.choice_label)


class RangeWidget(forms.MultiWidget):
    template_name = 'catalog/widgets/range_widget.html'

    def decompress(self, value):
        return value


class RangeField(forms.MultiValueField):
    default_error_messages = {
        'invalid_start': _('Введите валидное стартовое значение'),
        'invalid_end': _('Введите валидное конечное значение'),
    }

    def __init__(self, field_class=forms.IntegerField, *args, **kwargs):
        if 'initial' not in kwargs:
            kwargs['initial'] = ['', '']

        fields = (field_class(), field_class())

        super(RangeField, self).__init__(
            fields=fields,
            *args, **kwargs
        )

    def compress(self, data_list):
        if data_list:
            return [self.fields[0].clean(data_list[0]), self.fields[1].clean(data_list[1])]

        return None
