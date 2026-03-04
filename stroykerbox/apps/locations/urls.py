from django.urls import path

from .views import set_location


app_name = 'locations'

urlpatterns = [
    path('set-location/<int:location_id>/', set_location,
         name='set-location'),
]
