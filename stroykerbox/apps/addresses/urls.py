from django.urls import path

from . import views


app_name = 'addresses'

urlpatterns = [
    path('partners/', views.PartnerLocationListView.as_view(), name='partner-list'),
    # path('contacts/', views.ContactsPageView.as_view(), name='contacts-page'),
]
