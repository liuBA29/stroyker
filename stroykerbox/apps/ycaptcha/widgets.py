from typing import Optional
import uuid

from django.forms import widgets
from constance import config


class YandexCaptchaWidget(widgets.Widget):
    input_type = 'hidden'
    ycaptcha_field_name = 'smart-token'
    template_name = 'ycaptcha/widgets/ycaptcha_invisible.html'

    def __init__(self, submit_callback: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.submit_callback = submit_callback
        self.uuid = uuid.uuid4().hex
        self.attrs.setdefault('id', f'ycaptcha-container-{self.uuid}')
        self.attrs.setdefault('data-ycaptcha', '')
        self.attrs.setdefault('data-submit-callback', self.submit_callback or '')
        self.attrs.setdefault('data-site-key', config.YCAPTCHA_CLIENT_KEY)
        self.attrs.setdefault('data-shield-position', config.YCAPTCHA_SHIELD_POSITION)
        self.attrs.setdefault(
            'data-hide-shield', 'true' if config.YCAPTCHA_HIDE_SHIELD else ''
        )
        self.attrs.setdefault(
            'data-use-invisible', 'true' if config.YCAPTCHA_USE_INVISIBLE else ''
        )

    def value_from_datadict(self, data: dict, *args, **kwargs) -> str:
        return data.get(self.ycaptcha_field_name, None)

    def get_context(self, name: str, value: str, attrs: dict) -> dict:
        context = super().get_context(name, value, attrs)
        context.update(
            {
                'public_key': config.YCAPTCHA_CLIENT_KEY,
                'widget_uuid': self.uuid,
                'submit_callback': self.submit_callback,
            }
        )
        return context
