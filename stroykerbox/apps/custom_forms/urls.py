from django.urls import path, include

from .views import form_action


app_name = 'custom_forms'

urlpatterns = [
    path('fp/', include('django_drf_filepond.urls')),
    path('<slug:key>/', form_action, name='action'),
]
