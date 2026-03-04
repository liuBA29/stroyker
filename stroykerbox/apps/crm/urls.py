from django.urls import path

from .views import FeedbackMessageView, CallMeRequestView, GiftForPhoneRequestView


app_name = 'crm'

urlpatterns = [
    path('message/', FeedbackMessageView.as_view(),
         name='feedback-message-request'),
    path('callme-request/', CallMeRequestView.as_view(), name='callme-request'),
    path('gift-for-phone-requst/', GiftForPhoneRequestView.as_view(),
         name='gift-for-phone-request'),
]
