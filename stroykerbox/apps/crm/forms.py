from django import forms
from django.utils.translation import ugettext_lazy as _
from constance import config

from stroykerbox.apps.utils.forms import ReCaptchaFormMixin

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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone'] = forms.RegexField(regex=r'^\+?[78]\s?\(?\d{3}\)?\s?\d{3}-\d{2}-\d{2}$',
                                                error_messages={
                                                    'invalid': _(
                                                        'The phone number must begin with +7 or 7 or 8:'
                                                        ' "+7 (999) 999-99-99 or 7 (999) 999-99-99 or'
                                                        ' 8 (999) 999-99-99".')})
        for f in HIDDEN_EXT_FIELDS.values():
            if f in self.fields:
                self.fields[f].widget = forms.HiddenInput()

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
