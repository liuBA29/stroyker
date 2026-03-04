from django.urls import path

from .views import review_add, review_is_usefully, review_is_useless

app_name = 'reviews'

urlpatterns = [
    path('add/<int:product_pk>/', review_add, name='review_add'),
    path('usefully/<int:review_pk>/',
         review_is_usefully, name='review_usefully'),
    path('useless/<int:review_pk>/',
         review_is_useless, name='review_useless'),
]
