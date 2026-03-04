import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode
from django.utils.translation import ugettext_lazy as _

from constance import config
from stroykerbox.apps.utils.forms import ReCaptchaFormMixin

from .tasks import send_user_activation_email, new_registration_notify_manager
from .models import User


class LoginForm(AuthenticationForm):
    username = forms.CharField(max_length=254, widget=forms.widgets.EmailInput(
        attrs={'autocomplete': 'off', 'required': 'required', 'class': 'form-control'}))

    password = forms.CharField(label=_('Password'), widget=forms.PasswordInput(
        attrs={'autocomplete': 'off', 'required': 'required', 'class': 'form-control'}))

    remember_me = forms.BooleanField(required=False)

    def clean_username(self):
        return self.cleaned_data['username'].lower()


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'phone', 'name', 'company']

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        phone = re.sub(r'\D', '', phone)
        return phone


class RegistrationForm(ReCaptchaFormMixin, forms.ModelForm):
    password1 = forms.CharField(label=_('Password'), min_length=4,
                                widget=forms.PasswordInput(
                                    attrs={'class': 'form-control',
                                           'autocomplette': 'off',
                                           'required': 'required'}))
    password2 = forms.CharField(label=_('Password confirmation'),
                                widget=forms.PasswordInput(
                                    attrs={'class': 'form-control',
                                           'autocomplette': 'off',
                                           'required': 'required'}),
                                help_text=_('Enter the same password as above, for verification.'))

    class Meta:
        fields = ['email', 'name', 'company',
                  'phone', 'password1', 'password2']
        model = User
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control',
                                             'autocomplette': 'off',
                                             'required': 'required'}),
            'phone': forms.TextInput(attrs={'class': 'form-control',
                                            'autocomplette': 'off',
                                            }),
            'name': forms.TextInput(attrs={'class': 'form-control',
                                           'autocomplette': 'off',
                                           }),
            'company': forms.TextInput(attrs={'class': 'form-control',
                                              'autocomplette': 'off',
                                              }),
        }

    def captcha_enabled(self):
        if super().captcha_enabled():
            return config.RECAPTCHA_REGISTRATION_FORM

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _('A user with this email already exists.')
            )
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                _('Given passwords do not match'),
                code='password_mismatch',
            )
        return password2

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        phone = re.sub(r'\D', '', phone)
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data.get('password1'))

        if commit:
            user.last_login = timezone.now()
            user.save()

        return user

    @staticmethod
    def send_activation_email(request, user):
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        base_url = request.build_absolute_uri(reverse('registration_activate'))
        params = urlencode({'email': user.email, 'token': token})
        link = f'{base_url}?{params}'

        send_user_activation_email.delay(user, link)

    @staticmethod
    def send_manager_activation_email(account):
        new_registration_notify_manager.delay(account)


class UserActivationForm(forms.ModelForm):
    token = forms.CharField(max_length=128)

    class Meta:
        model = User
        fields = ('token',)

    def clean_token(self):
        """
        Check if token is valid
        """
        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(self.instance, self.cleaned_data.get('token')):
            raise forms.ValidationError(_('Activation token is not valid'))

    def save(self, commit=True):
        user = super(UserActivationForm, self).save(commit=False)
        user.is_active = True
        if commit:
            user.save()
        return user


class MyPasswordResetForm(PasswordResetForm):
    """
    Password reset form
    """

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            raise forms.ValidationError(_("That email address doesn't have an associated user account. "
                                          "Are you sure you've registered?"))
        return email
