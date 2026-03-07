from django import forms
from django.utils.translation import ugettext_lazy as _
from constance import config

from stroykerbox.apps.utils.forms import ReCaptchaFormMixin
from stroykerbox.apps.utils.utils import clear_phone as clear_phone_util

from .models import FeedbackMessageRequest, CallMeRequest, GiftForPhoneRequest


HIDDEN_EXT_FIELDS = dict(
    UTM_CAMPAIGN_FIELDNAME='utm_campaign',
    UTM_CONTENT_FIELDNAME='utm_content',
    UTM_MEDIUM_FIELDNAME='utm_medium',
    UTM_SOURCE_FIELDNAME='utm_source',
    UTM_TERM_FIELDNAME='utm_term',
    PAGE_URL_FIELDNAME='page_url'
)


class CrmFormBase(ReCaptchaFormMixin, forms.ModelForm):
    # Формат: +7/7/8 и 10 цифр; допускаются пробелы, скобки, дефисы или просто 11 цифр (89171234567).
    PHONE_REGEX = r'^(\+?[78]\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}|[78]\d{10})$'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone'] = forms.RegexField(
            regex=self.PHONE_REGEX,
            error_messages={
                'invalid': _(
                    'Укажите номер в формате: +7 (999) 999-99-99 или 8 (999) 999-99-99'
                ),
            },
        )
        for f in HIDDEN_EXT_FIELDS.values():
            if f in self.fields:
                self.fields[f].widget = forms.HiddenInput()

    def clean_phone(self):
        """Нормализует телефон к формату 8 (XXX) XXX-XX-XX для сохранения."""
        value = self.cleaned_data.get('phone')
        if not value or not str(value).strip():
            return value
        raw = clear_phone_util(value, country_code=7)
        if not raw or len(raw) < 10:
            raise forms.ValidationError(
                _('Укажите корректный номер телефона (10 цифр после кода страны).')
            )
        digits = raw[-10:]
        return '8 ({}) {}-{}-{}'.format(digits[:3], digits[3:6], digits[6:8], digits[8:])

    class Media:
        js = ('crm/js/crm_forms.js',)


class FeedbackMessageForm(CrmFormBase):
    SUBMIT_CALLBACK = 'feedback_form_ajax_submit'

    def captcha_enabled(self):
        if super().captcha_enabled():
            return config.RECAPTCHA_FEEDBACK_FORM

    class Meta:
        model = FeedbackMessageRequest
        fields = ('name', 'email', 'phone', 'message',
                  *HIDDEN_EXT_FIELDS.values())
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': _('What is your name'),
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control input_error__state', 'placeholder': _('Your E-Mail')
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': _('Your phone')
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control', 'placeholder': _('What are you interested in?')
            }),
        }


class CallMeForm(CrmFormBase):

    SUBMIT_CALLBACK = 'callme_form_ajax_submit'

    def captcha_enabled(self):
        if super().captcha_enabled():
            return config.RECAPTCHA_CALLME_FORM

    class Meta:
        model = CallMeRequest
        fields = ('name', 'phone', *HIDDEN_EXT_FIELDS.values())


class GiftForPhoneRequestForm(forms.ModelForm):

    class Meta:
        model = GiftForPhoneRequest
        fields = ('phone', *HIDDEN_EXT_FIELDS.values())
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control phone',
            }),
        }

    class Media:
        js = ('crm/js/crm_forms.js',)
