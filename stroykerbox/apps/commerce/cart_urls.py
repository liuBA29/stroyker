from django.urls import path

from stroykerbox.apps.commerce import views as cart_views

app_name = 'cart'

urlpatterns = [
    path('', cart_views.cart, name='cart'),
    path('add/<int:product_pk>', cart_views.add_to_cart, name='add_to_cart'),
    path(
        'ajax/mini-cart-8march/',
        cart_views.ajax_mini_cart_8march,
        name='ajax_mini_cart_8march',
    ),
    path('ajax-add-to-cart-related/', cart_views.ajax_add_to_cart_related, name='ajax_add_to_cart_related'),
    path(
        'ajax_get_delivery_to_address_cost/',
        cart_views.AjaxGetDeliveryToAddressCost.as_view(),
        name='ajax_get_delivery_to_address_cost',
    ),
    path(
        'ajax_get_delivery_to_tc_cost/',
        cart_views.AjaxGetDeliveryToTCCost.as_view(),
        name='ajax_get_delivery_to_tc_cost',
    ),
    path('confirm/', cart_views.cart_confirm, name='confirm'),
    path('del/<int:product_pk>', cart_views.remove_from_cart, name='remove_from_cart'),
    path('delivery/', cart_views.cart_delivery, name='delivery'),
    path('delivery_calculator/', cart_views.delivery_calculator, name='delivery_calculator'),
    path('failed/', cart_views.CartFailed.as_view(), name='failed'),
    path('order-invoice-html/<int:order_pk>', cart_views.order_invoice_html, name='order-invoice-html'),
    path('order-invoice-pdf/<int:order_pk>', cart_views.order_invoice_pdf, name='order-invoice-pdf'),
    path('order-status/', cart_views.status, name='order-status'),
    path('payment/', cart_views.cart_payment, name='payment'),
    path('success/', cart_views.cart_success, name='success'),
    path('upd/<int:product_pk>', cart_views.update_product_quantity, name='update_product_quantity'),
    path('yookassa/confirm/<slug:slug>/', cart_views.yookassa_confirm, name='yookassa_confirm'),
]
