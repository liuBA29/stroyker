from django import forms
from django.core.exceptions import ValidationError

from stroykerbox.apps.smartlombard.forms import SLCheckDebtForm
from .services.smartlombard_api import SmartlombardAPI


class TBankPaymentForm(forms.Form):
    ticket_number = forms.CharField(widget=forms.HiddenInput())
    amount = forms.IntegerField(widget=forms.HiddenInput())


class SLTicketInfoForm(SLCheckDebtForm):
    ticket_number = forms.CharField(label='Номер билета')

    def clean(self):
        cleaned_data = super().clean()

        ticket_number = cleaned_data.get('ticket_number')

        api = SmartlombardAPI()
        ticket_dept = api.get_ticket_debt(ticket_number)

        if api.errors:
            msg = '\n'.join(api.errors)
            raise ValidationError(msg)
        else:
            self.ticket_info = cleaned_data
            self.ticket_info['debt'] = ticket_dept
