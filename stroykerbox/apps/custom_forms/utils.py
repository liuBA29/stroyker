import binascii
import os

from django.utils import timezone
from django.utils.encoding import force_str, smart_str

custom_form_help_text = (
    'Для вставки "кастомных форм" внутрь текста, '
    'используйте соответствующую метку: {% custom_form "КЛЮЧ-НУЖНОЙ-КАСТОМНОЙ-ФОРМЫ" %}'
)


def random_filedir(path: str, depth=2) -> str:
    dirname = os.path.normpath(force_str(timezone.now().strftime(smart_str(path))))
    hash = binascii.hexlify(os.urandom(20 + depth)).decode()
    for q in range(depth):
        append, hash = hash[:2], hash[2:]
        dirname = os.path.join(dirname, append)
    return os.path.join(dirname, "%s/" % hash)
