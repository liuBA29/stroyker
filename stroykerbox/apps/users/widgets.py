from django import forms
from django.forms.widgets import SelectDateWidget


class RadioSelectCustom(forms.widgets.RadioSelect):
    option_template_name = 'users/widgets/radio_select_option_widget.html'
    template_name = 'users/widgets/radio_select_widget.html'


class SelectDateWidgetCustom(SelectDateWidget):
    template_name = 'users/widgets/select_date_widget.html'
