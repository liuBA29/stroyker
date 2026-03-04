from django.urls import path

from .views import item_details, item_list
from .models import NEWS_POST_TYPE_NEWS, NEWS_POST_TYPE_PROMO

app_name = 'news'

news_context = {
    'post_type': NEWS_POST_TYPE_NEWS
}
promo_context = {
    'post_type': NEWS_POST_TYPE_PROMO
}

urlpatterns = [
    path('', item_list, name='all_list'),
    path('news/', item_list, news_context, name='news_list'),
    path('news/<slug:slug>/', item_details, news_context, name='news_details'),
    path('promo/', item_list, promo_context, name='promo_list'),
    path('promo/<slug:slug>/', item_details, promo_context, name='promo_details')
]
