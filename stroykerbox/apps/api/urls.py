from django.urls import path, include

from rest_framework import routers
from rest_framework.documentation import include_docs_urls

from .catalog import views as catalog_views
from .commerce.views import OrderViewSet
from .users.views import UserViewSet
from .crm.views import CrmRequestBaseViewSet

router = routers.DefaultRouter()


# Catalog app routers
router.register(
    r'products-common', catalog_views.ProductViewSet, basename='products_common'
)
router.register(
    r'products-stock', catalog_views.ProductStockViewSet, basename='products_stock'
)
router.register(
    r'product-prices', catalog_views.ProductPriceViewSet, basename='product_prices'
)
router.register(
    r'product-units', catalog_views.ProductUomViewSet, basename='product_units'
)
router.register(r'crm', CrmRequestBaseViewSet, basename='crm')
router.register(
    r'catalog-categories', catalog_views.CategoryViewSet, basename='catalog_categories'
)

# Users app routers
router.register(r'users', UserViewSet, basename='users')

# Commerce app routers
router.register(r'orders', OrderViewSet, basename='orders')


urlpatterns = [
    path(
        'product-images/<str:product_sku>/',
        catalog_views.ProductImagesView.as_view(),
        name='product_images',
    ),
    path(
        'product-images/<str:product_sku>/delete/',
        catalog_views.ProductImagesDeleteView.as_view(),
        name='product_images_delete',
    ),
    path(
        'docs/', include_docs_urls(title='StroykerBox API Documentation', public=False)
    ),
    path('stats/', include('stroykerbox.apps.api.stats.urls')),
    path('search/', include('stroykerbox.apps.search.api.urls')),
    path(
        'product-bulk-update/prices/',
        catalog_views.ProductPricesBulkUpdate.as_view(),
        name='product_bulk_update_prices',
    ),
    path(
        'product-bulk-update/stock/',
        catalog_views.ProductStocksBulkUpdate.as_view(),
        name='product_bulk_update_stock',
    ),
] + router.urls
