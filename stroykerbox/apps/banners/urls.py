from django.urls import path

from .views import ajax_increase_click_counter, ajax_increase_view_counter

app_name = 'banners'

urlpatterns = [
    path('ajax/view-cnt-incr', ajax_increase_view_counter, name='views-increment'),
    path('ajax/clck-cnt-incr', ajax_increase_click_counter, name='clicks-increment'),
]
