from django.urls import path

from .views import ArticleList, ArticleDetails

app_name = 'articles'

urlpatterns = [
    path('', ArticleList.as_view(), name='article-list'),
    path('<slug:slug>/', ArticleDetails.as_view(), name='article-details'),
]
