from django_rq import job

from .helper import Novofon, novofon_enabled


@job
def update_novofon_stats():
    if novofon_enabled:
        Novofon().process_stats()
