from django.contrib import admin
from django.db.models import JSONField

from stroykerbox.apps.utils.widgets import PrettyJSONWidget

from .models import B24Log


@admin.register(B24Log)
class B24LogAdmin(admin.ModelAdmin):
    formfield_overrides = {JSONField: {'widget': PrettyJSONWidget}}
