import json
from typing import Any, Optional
import hashlib
from logging import getLogger

from django.conf import settings
from django.http import HttpRequest
from django.urls import reverse
import requests
from constance import config

from stroykerbox.apps.smartlombard.tbank import (
    TBANK_SUCCESS_URL,
    TBANK_FAIL_URL,
)


TBANK_API_MAIN_URL = 'https://securepay.tinkoff.ru/v2/'


logger = getLogger(__name__)


class TBankAPI:
    def get_request_data(self, request: HttpRequest) -> Optional[dict]:
        try:
            data = json.loads(request.body)
        except Exception as e:
            logger.exception(e)
            return None

        request_sign = data.pop('Token')
        self_sign = self.get_token_sign(**data)

        if request_sign == self_sign:
            return data

    @staticmethod
    def get_qr(value: str) -> Optional[str]:
        try:
            import qrcode
            import qrcode.image.svg
        except ModuleNotFoundError:
            return None

        factory = qrcode.image.svg.SvgPathImage
        img = qrcode.make(
            value, image_factory=factory, box_size=config.TBANK_QR_BOX_SIZE
        )

        return img.to_string(encoding='unicode')

    def get_token_sign(self, **kwargs) -> str:
        """
        https://www.tbank.ru/kassa/dev/funding/#section/Podpis-zaprosa
        """
        data = {
            'Password': config.TBANK_PASSWORD,
        }
        data.update({k: str(v) for k, v in kwargs.items()})

        sign_dict = dict(sorted(data.items()))
        sign_str = ''.join(sign_dict.values())
        return hashlib.sha256(sign_str.encode()).hexdigest()

    def payment_init(self, order_id: str, amount: int) -> dict:
        """
        https://www.tbank.ru/kassa/dev/funding/#tag/Priem-perevodov-dlya-Merchantov-bez-PCI-DSS
        """
        base_url = settings.BASE_URL.rstrip('/')
        sign_dict: dict[str, Any] = {
            'TerminalKey': config.TBANK_TERMINAL_KEY,
            'Amount': amount,
            'OrderId': order_id,
            'SuccessURL': f'{base_url}{TBANK_SUCCESS_URL}',
            'FailURL': f'{base_url}{TBANK_FAIL_URL}',
        }
        if not settings.DEBUG and not base_url.endswith('local'):
            sign_dict['NotificationURL'] = f'{base_url}{reverse("tbank:notify")}'

        token = self.get_token_sign(**sign_dict)

        data = {'Token': token}
        data |= sign_dict

        url = f'{TBANK_API_MAIN_URL}Init'
        output = {}
        try:
            response = requests.post(url, json=data)
            output = response.json()
        except Exception as e:
            logger.exception(e)

        if not output.get('Success'):
            logger.error(output)

        return output

    def get_payment_status(self, payment_id: str) -> dict:
        output = {}
        sign_dict: dict[str, Any] = {
            'TerminalKey': config.TBANK_TERMINAL_KEY,
            'PaymentId': payment_id,
        }
        token = self.get_token_sign(**sign_dict)

        data = {'Token': token}
        data |= sign_dict

        url = f'{TBANK_API_MAIN_URL}GetState'

        try:
            response = requests.post(url, json=data)
            output = response.json()
        except Exception as e:
            logger.exception(e)

        if not output.get('Success'):
            logger.error(output)

        return output
