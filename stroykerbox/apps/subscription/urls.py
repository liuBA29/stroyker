from django.urls import path
from stroykerbox.apps.subscription import views


app_name = 'subscription'

urlpatterns = [
    path('new/', views.SubscriptionNewView.as_view(), name='new'),
]
