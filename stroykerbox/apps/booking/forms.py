from django import forms
from constance import config

from stroykerbox.apps.utils.forms import ReCaptchaFormMixin


class BookingForm(ReCaptchaFormMixin, forms.Form):
    name = forms.CharField(max_length=254)
    phone = forms.CharField(max_length=18)
    message = forms.CharField(widget=forms.Textarea())

    def captcha_enabled(self):
        if super().captcha_enabled():
            return config.CAPTCHA_USE_FOR_BOOKING_FORM
