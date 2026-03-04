from functools import reduce
import operator

from django.contrib.postgres.search import SearchVector, SearchVectorField
from django.db.models import Value

from constance import config


def staticpage_search_enabled():
    return config.SEARCH__USE_FULLTEXT and any((
        config.SEARCH_STATICPAGE_TITLE,
        config.SEARCH_STATICPAGE_TEXT,
    ))


def update_staticpage_search_index(page):
    components = None
    if hasattr(page, 'index_components'):
        components = page.index_components()
    if not components:
        return
    pk = page.pk

    search_vectors = []
    for weight, text in components.items():
        search_vectors.append(
            SearchVector(Value(text, output_field=SearchVectorField()),
                         weight=weight, config='russian')
        )
    return page.__class__.objects.filter(pk=pk).update(
        search_document=reduce(operator.add, search_vectors)
    )
