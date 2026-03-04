from logging import getLogger

import requests
from constance import config
from django.conf import settings

logger = getLogger('b24')


class B24:
    LEAD_ADD_METHOD = 'crm.lead.add'
    LEAD_UPDATE_METHOD = 'crm.lead.update'

    def __init__(self):
        web_hook_url = config.B24_WEBHOOK_URL

        if not web_hook_url.endswith('/'):
            web_hook_url += '/'
        self.web_hook = web_hook_url

    def add_lead(self, fields_data: dict) -> requests.models.Response | None:
        url = f'{self.web_hook}{self.LEAD_ADD_METHOD}'
        data = {'fields': fields_data}
        if settings.DEBUG:
            logger.debug(data)
            return None
        return requests.post(url, json=data)

    def update_lead(
        self, lead_id: int, fields_data: dict
    ) -> requests.models.Response | None:
        url = f'{self.web_hook}{self.LEAD_UPDATE_METHOD}'
        data = {'id': lead_id, 'fields': fields_data}
        if settings.DEBUG:
            logger.debug(data)
            return None

        return requests.post(url, json=data)
