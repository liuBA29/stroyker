from typing import Optional
from decimal import Decimal

from django.core.cache import cache
from constance import config
import requests

SMARTLOMBARD_API_BASE_URL = 'https://online.smartlombard.ru/api/exchange/v1'
TOKEN_CACHE_LIFETIME_SEC = 86000


class SmartlombardAPI:
    def __init__(self):
        self.errors = []
        self.access_token = self._get_access_token()

    def get_headers(self):
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
        }

    def _get_access_token(self, refresh=False) -> str | None:
        # return 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMDg3NiwiZXhwIjoxNzQ4MzQ2NzE0LCJpc3MiOiJzbWFydGxvbWJhcmQucnUiLCJpYXQiOjE3NDgyNjAzMTR9.liLybEplfTWCKtm5PUTAxz9yUiBofcdoXa5IkqdPha0'  # noqa
        if not all(
            (
                config.SMARTLOMBARD_API_ACCOUNT_ID,
                config.SMARTLOMBARD_API_SECRET_KEY,
            )
        ):
            return None

        key = 'smartlombard_api_token'

        if not refresh and (token := cache.get(key)):
            return token

        url = f'{SMARTLOMBARD_API_BASE_URL}/auth/access_token'
        response = requests.post(
            url,
            data={
                'account_id': config.SMARTLOMBARD_API_ACCOUNT_ID,
                'secret_key': config.SMARTLOMBARD_API_SECRET_KEY,
            },
        )
        if response.status_code == 200:
            response_data = response.json()
            token = response_data.get('result', {}).get('access_token', {}).get('token')

            if token:
                cache.set(key, token, TOKEN_CACHE_LIFETIME_SEC)
                return token
        else:
            self.errors.append(
                'Не удается получить токен доступа к API. Проверьте настройки '
                'SMARTLOMBARD_API_ACCOUNT_ID и'
                'SMARTLOMBARD_API_SECRET_KEY'
            )

    def get_ticket_info_by_number(self, ticket_number: str) -> dict:
        output = {}
        url = f'{SMARTLOMBARD_API_BASE_URL}/pawn_tickets'
        response = requests.get(
            url, params={'document_number': ticket_number}, headers=self.get_headers()
        )
        output = response.json()
        if response.status_code != 200:
            self.errors.append(
                f'Ошибка получения данных. Код ответа: {response.status_code}'
            )
        return output

    def get_ticket_debt(self, ticket_number: str) -> Optional[Decimal]:
        data = self.get_ticket_info_by_number(ticket_number)
        if not data:
            return None
        try:
            loan_amount = data['result']['pawn_tickets'][0]['loan_amount']
            debt_str = data['result']['pawn_tickets'][0]['pawn_ticket_debt']['sum_debt']
            return Decimal(loan_amount) + Decimal(debt_str)
        except Exception as e:
            self.errors.append(str(e))

    def get_ticket_info(self, ticket_id: int) -> dict:
        output = {}
        if self.access_token:
            url = f'{SMARTLOMBARD_API_BASE_URL}/pawn_tickets/{ticket_id}'
            response = requests.get(url, headers=self.get_headers())

            if response.status_code == 200:
                output = response.json()
            else:
                self.errors.append(
                    f'Ошибка получения данных. Код ответа: {response.status_code}'
                )
        return output
