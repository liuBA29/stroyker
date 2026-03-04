from django.urls import path

from .views import FaqPage


app_name = 'faq'

urlpatterns = [
    path('', FaqPage.as_view(), name='index'),
]
