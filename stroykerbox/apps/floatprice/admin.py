# from django.contrib import admin

# from .models import FloatPrice


# @admin.register(FloatPrice)
# class FloatPriceAdmin(admin.ModelAdmin):
#     list_display = ('product_name', 'product_sku', 'product_price', 'price')
#     readonly_fields = ('product', 'created_at', 'updated_at')

#     def product_name(self, obj):
#         return obj.product.name

#     def product_sku(self, obj):
#         return obj.product.sku

#     def product_price(self, obj):
#         return obj.product.price
