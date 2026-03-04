from django.contrib import admin

from .models import ProductReview


class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating_value', 'created_at', 'published')
    list_filter = ('user', 'rating_value', 'created_at')
    list_display_links = ('product', 'user', 'created_at')
    raw_id_fields = ('product',)


admin.site.register(ProductReview, ProductReviewAdmin)
