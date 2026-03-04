from django.urls import path

from .views import custom_colors_css


app_name = 'customization'

urlpatterns = [
    path('custom_colors.css', custom_colors_css,
         name='custom-colors-css'),
]
