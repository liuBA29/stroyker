from django.urls import path

from . import views

app_name = 'tbank'

urlpatterns = [
    path('prepayment/', views.tbank_prepayment, name='prepayment'),
    path('payment/<str:ticket_number>/', views.tbank_payment, name='payment'),
    path('notify/', views.tbank_notify, name='notify'),
]
