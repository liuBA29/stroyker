from django.contrib import admin
from django.utils import timezone

from .models import Article


class ArticleAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('related_products',)
    autocomplete_lookup_fields = {
        'm2m': ['related_products'],
    }

    def save_model(self, request, obj, form, change):
        if not obj.created:
            obj.created = timezone.now()
        obj.save()


admin.site.register(Article, ArticleAdmin)
