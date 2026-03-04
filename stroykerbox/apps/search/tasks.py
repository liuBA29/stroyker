from typing import Any, Optional

from django.apps import apps
from django.contrib.auth import get_user_model
from django_rq import job


User = get_user_model()


@job('default')
def create_search_query_data_object(
    query_string: str, meta_data: dict[str, Any], user_id: Optional[int | str]
) -> Optional[str]:

    SearchQueryData = apps.get_model('search.SearchQueryData')

    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            user = None

        try:
            SearchQueryData.objects.create(
                query=query_string, user=user, meta_data=meta_data
            )
        except Exception as e:
            return f'ERROR: {e}'
    return 'OK'
