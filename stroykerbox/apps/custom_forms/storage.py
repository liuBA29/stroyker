from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class FilePondStorage(FileSystemStorage):
    pass
