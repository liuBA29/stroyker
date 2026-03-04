import tempfile

from django.core.cache import cache


def create_test_imagefile():
    return tempfile.NamedTemporaryFile(suffix=".jpg").name


def clearcache():
    cache.clear()
