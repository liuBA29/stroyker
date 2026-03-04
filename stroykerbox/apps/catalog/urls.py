from django.urls import path

from stroykerbox.apps.catalog import views


app_name = 'catalog'

urlpatterns = [
    path('', views.CatalogIndexView.as_view(), name='index'),
    path('<slug:category_slug>/', views.CategoryView.as_view(), name='category'),
    path(
        'ajax-get-mod-for-product/<int:source_product_pk>/<path:mod_code>/',
        views.ajax_get_product_mod_url,
        name='ajax_get_mod_for_product',
    ),
    path(
        'ajax_chart_prices_data/',
        views.AjaxChartPrices.as_view(),
        name='ajax_chart_prices_data',
    ),
    path(
        'category/<slug:category_slug>/<slug:subcategory_slug>/',
        views.CategoryView.as_view(),
        name='subcategory',
    ),
    path('comparison/', views.comparison, name='comparison'),
    path('comparison/add/', views.comparison_add, name='comparison_add'),
    path('comparison/del/', views.comparison_del, name='comparison_del'),
    path(
        'export/<slug:category_slug>/',
        views.export_category_products_xls,
        name='export-category-products',
    ),
    path(
        'product/<slug:category_slug>/<slug:product_slug>/',
        views.RedirectToProductView.as_view(),
        name='redirect_to_product_view',
    ),
    path(
        'product/<slug:product_slug>/', views.ProductView.as_view(), name='product_view'
    ),
    path('search', views.ProductSearchResult.as_view(), name='product-search'),
    path(
        'heavy_pictures_products.xml',
        views.heavy_picture_products_xml,
        name='download-heavy-picture-products-xml',
    ),
]
