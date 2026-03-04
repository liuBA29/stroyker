from django.urls import path

from stroykerbox.apps.users import views

app_name = 'users'

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/saved/', views.profile, {'saved': True}, name='profile_saved'),
    path('orders/', views.orders_list, name='orders_list'),
    path('orders/<int:order_pk>/', views.order_details, name='order_details'),
    path('docs/', views.user_document_list, name='docs_index_list'),
    path('docs/<int:year>/', views.user_document_list, name='docs_year_list'),
    path(
        'docs/<int:year>/<int:month>/', views.user_document_list, name='docs_month_list'
    ),
]
