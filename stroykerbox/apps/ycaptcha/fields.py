import logging
import sys
import uuid

from django import forms
from django.core.exceptions import ImproperlyConfigured, ValidationError

from constance import config

from .widgets import YandexCaptchaWidget
from . import client

logger = logging.getLogger(__name__)


class YandexCaptchaField(forms.CharField):
    widget = YandexCaptchaWidget
    err_msg = 'Yandex Smart Captcha: ошибка проверки.'
    default_error_messages = {
        "captcha_invalid": err_msg,
        "captcha_error": err_msg,
    }

    def __init__(self, public_key=None, private_key=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not isinstance(self.widget, YandexCaptchaWidget):
            raise ImproperlyConfigured(
                'ycaptcha.fields.YandexCaptchaField.widget'
                ' должен быть экземпляром класса ycaptcha.widgets.YandexCaptchaWidget или производным от него.'
            )

        self.required = True

        self.private_key = private_key or config.YCAPTCHA_SERVER_KEY
        self.public_key = public_key or config.YCAPTCHA_CLIENT_KEY

    def get_client_ip(self) -> str:
        f = sys._getframe()
        while f:
            request = f.f_locals.get('request')
            if request:
                remote_ip = request.META.get('REMOTE_ADDR', '')
                forwarded_ip = request.META.get('HTTP_X_FORWARDED_FOR', '')
                ip = remote_ip if not forwarded_ip else forwarded_ip
                return ip
            f = f.f_back  # type: ignore

    def validate(self, value: str) -> None:
        super().validate(value)
        check_captcha = None
        try:
            check_captcha = client.check_captcha(
                token=value,
                remoteip=self.get_client_ip(),
                private_key=self.private_key,
            )

        except Exception as e:
            logger.exception(str(e))

        if not check_captcha:
            raise ValidationError(
                self.error_messages['captcha_invalid'], code='captcha_invalid'
            )
