import requests
from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from constance import config

from .models import TicketStock

SMARTLOMBARD_CHECK_DEPT_URL = 'https://online.smartlombard.ru/api/debt/get'


class SLCheckDebtForm(forms.Form):
    client_surname = forms.CharField(label=_('surname'))
    ticket_number = forms.CharField(label=_('ticket_number'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ticket_info = None

    def get_response_json(self, data: dict) -> dict:
        """
        Expectec dict with the info example:
            {
                'buyout_date': '25.05.2022',
                'datetime': '25.04.2022 16:13',
                'goods': ['bosch gsr 120-li'],
                'online_prolongation_url': 'https://online.smartlombard.ru/public/online_prolongation/?org_id=6045&workplace_id=7&token=ce8bcb59ec3e243e1bfc7b72dc9b9a63&number=ОТ010930',  # noqa
                'summ': '75 руб.'
            }
        """
        output = {}
        response = requests.post(SMARTLOMBARD_CHECK_DEPT_URL, data=data, verify=False)
        if hasattr(response, 'json'):
            output = response.json()
        return output

    def clean(self):
        cleaned_data = super().clean()
        number = cleaned_data.get('ticket_number', '')
        try:
            ticket_stock = TicketStock.objects.get(code__iexact=number[:2])
        except TicketStock.DoesNotExist:
            self.add_error('ticket_number', 'Неизвестный код билета')
            return cleaned_data

        # https://redmine.fancymedia.ru/issues/12870
        if ticket_stock.is_closed:
            self.ticket_info = {
                'is_closed': True,
                'msg_for_closed': ticket_stock.msg_for_closed,
            }
            return

        data = {
            'client_surname': cleaned_data.get('client_surname', ''),
            'organization': config.SMARTLOMBARD_PROFILE_ID,
            'workplace': ticket_stock.stock.third_party_code,
            'number': number,
        }

        response = self.get_response_json(data)

        if 'error' in response:
            raise ValidationError(response['error'])
        else:
            self.ticket_info = cleaned_data
            self.ticket_info.update(response)
        return cleaned_data
