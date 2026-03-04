from django.utils.translation import ugettext_lazy as _
from django.core.validators import RegexValidator


def phone_validator(phone):
    pattern = r'^\+?[78]\s?\(?\d{3}\)?\s?\d{3}-\d{2}-\d{2}$'

    validator = RegexValidator(
        pattern,
        message=_(
            'The phone number must begin with +7 or 7 or 8: '
            '"+7 (999) 999-99-99 or 7 (999) 999-99-99 or 8 (999) 999-99-99".')
    )
    return validator(phone)
