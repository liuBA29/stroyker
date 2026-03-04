from datetime import datetime
from django.urls import path, register_converter

from . import views


class DateConverter:
    regex = r'\d{4}-\d{1,2}-\d{1,2}'
    format = '%Y-%m-%d'

    def to_python(self, value):
        return datetime.strptime(value, self.format).date()

    def to_url(self, value):
        return value.strftime(self.format)


register_converter(DateConverter, 'date')

app_name = 'booking'

urlpatterns = [
    path('matrix/<slug:key>/',
         views.MatrixPage.as_view(), name='matrix_page'),
    path('matrix/<slug:key>/<date:custom_date>/',
         views.MatrixPage.as_view(), name='matrix_page_custom_date'),
    path('matrix/<slug:itemset_key>/add/<int:item_id>/<date:reserve_date>/',
         views.add_reserve, name='add_date_reserve'),
    path('matrix/<slug:itemset_key>/add/<int:item_id>/<date:reserve_date>/<int:hour>/',
         views.add_reserve, name='add_hour_reserve'),
]
