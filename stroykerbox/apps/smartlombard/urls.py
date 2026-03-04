from django.urls import path

from .views import lombard_receiver

app_name = 'smartlombard'

urlpatterns = [
    path('', lombard_receiver, name='receiver'),
]
