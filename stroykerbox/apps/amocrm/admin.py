from django.contrib import admin

from . import models


@admin.register(models.CustomFormFieldAMO)
class CustomFormFieldAMOAdmin(admin.ModelAdmin):
    list_display = ('field_object', 'amo_id')
    list_editable = ('amo_id',)
