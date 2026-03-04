from django_rq import job

from .utils import update_staticpage_search_index
from .models import Page


@job
def search_index_updater(instance_id):
    try:
        page = Page.objects.get(pk=instance_id)
    except Page.DoesNotExist:
        return f'Page with ID "{instance_id}" not found.'
    update_staticpage_search_index(page)
