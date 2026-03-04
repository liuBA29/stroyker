from collections import defaultdict

from django.db import models
from django.contrib.auth import get_user_model
from django.core.cache import cache


User = get_user_model()

SEARCH_ALIASES_CACHE_KEY = 'search_word_aliases'


class SearchQueryData(models.Model):
    META_FOR_SAVE = ('HTTP_', 'REMOTE_')

    query = models.CharField('поисковый запрос', max_length=128)
    created_at = models.DateTimeField('дата/время запроса', auto_now_add=True)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='search_queries',
    )
    meta_data = models.JSONField('meta-данные запроса', default=dict)

    def __str__(self):
        return f'{self.query}: {self.created_at}'

    class Meta:
        verbose_name = 'поисковый запрос'
        verbose_name_plural = 'поисковые запросы'
        ordering = ('-created_at',)


class SearchWordAlias(models.Model):
    """
    https://redmine.nastroyker.ru/issues/15874
    """

    search_word = models.CharField(
        'слово', max_length=32, help_text='Слово, введенное в поисковую строку.'
    )
    alias = models.CharField(
        'алиас', max_length=32, help_text='Алиас поискового слова.'
    )

    def __str__(self):
        return f'{self.search_word}:{self.alias}'

    class Meta:
        verbose_name = 'поисковый алияс'
        verbose_name_plural = 'поисковые алиясы'

    @classmethod
    def create_search_aliases_cache(cls) -> dict[str, list[str]]:
        output = defaultdict(list)
        for word, alias in SearchWordAlias.objects.values_list('search_word', 'alias'):
            output[word].append(alias)
        cache.set(SEARCH_ALIASES_CACHE_KEY, output, None)
        return output
