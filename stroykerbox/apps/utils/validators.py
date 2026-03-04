import xml.etree.cElementTree as et

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, URLValidator, validate_image_file_extension
from django.utils.translation import gettext_lazy as _
from slugify import slugify


def validate_svg_or_image(file):
    if file.name.endswith('.svg'):
        return validator_svg(file)
    return validate_image_file_extension(file)


def url_or_path_validator(value):
    if '://' in value:
        validator = URLValidator()
    else:
        pattern = r'^(/([\w=&/?-]+)*)?/$'
        validator = RegexValidator(
            pattern,
            message=_('must start and end with a slash if it is a '
                      'relative path or start with http://..., if it is a full URL'))
        value = value.split('?')[0]
    return validator(value)


class CustomURLValidator(URLValidator):
    def __call__(self, value):
        if '://' not in value:
            value = f'http://somehost.com{value}'
        super().__call__(value)


def is_svg(f):
    """
    Check if provided file is svg
    """
    try:
        f.seek(0)
    except FileNotFoundError:
        raise ValidationError(f'Файл {f.name} отсутствует на сервере.')

    tag = None
    try:
        for event, el in et.iterparse(f, ('start',)):
            tag = el.tag
            break
    except et.ParseError:
        pass
    return tag == '{http://www.w3.org/2000/svg}svg'


def validator_svg(file):
    if not is_svg(file):
        raise ValidationError(_('File is not SVG'))


class ValidateSlug:
    """
    Test whether the given value is an accepted slug.

    The class can test against custom slug functions (e.g. awesome-slugify).
    It should be used instead of the standard slug validators,
    because these only accept what the standard Django slugify() can process.
    """

    slugify = slugify
    message = _("Enter a valid slug.")
    code = "invalid"

    def __init__(self, message=None, code=None):
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code

    def __call__(self, value):
        if slugify(value) != value:
            raise ValidationError(self.message, code=self.code)
