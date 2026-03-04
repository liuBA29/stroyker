from django.urls import re_path

from .views import StaticPageView

app_name = 'staticpages'

urlpatterns = [
    re_path(r'^(?P<url>.*)/$', StaticPageView.as_view(), name='staticpage'),
]
