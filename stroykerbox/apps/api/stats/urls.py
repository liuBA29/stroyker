from django.urls import path

from . import views


urlpatterns = [
    path('', views.StatsInfo.as_view()),
    path(
        'active-product-count/',
        views.ActiveProductCount.as_view(),
        name='active_product_count',
    ),
    path('cart/orders/', views.CartOrderStatsView.as_view()),
    path('cart/amounts/', views.CartAmountStatsView.as_view()),
    path('cart/top-products/', views.CartTopProductsStatsView.as_view()),
    path('banners/', views.BannerStatsView.as_view()),
    path('crm/', views.CrmStatsView.as_view()),
    path('crm/<str:object_class>/', views.CrmStatsView.as_view()),
    path('social/', views.SocialInfoView.as_view()),
    path('social/<str:service>/', views.SocialInfoView.as_view()),
    path('product_by_path/<path:product_path>', views.ProductInfoByPath.as_view()),
    path('custom_form/', views.CustomFormStatsView.as_view()),
    path('custom_form/<str:form_key>/', views.CustomFormStatsView.as_view()),
    path('version-info/', views.VersionInfo.as_view()),
    path('price-history/', views.PriceHistoryInfo.as_view()),
    path('news-updates/', views.NewsUpdatesInfo.as_view()),
    path('content-quality-value/', views.ContentQualityValue.as_view()),
    path('content-quality-value-product/', views.ContentQualityValueProduct.as_view()),
]
