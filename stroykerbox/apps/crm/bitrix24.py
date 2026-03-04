from django.conf import settings
import requests


class B24:
    LEAD_ADD_METHOD = 'crm.lead.add'

    def __init__(self, crm_obj, web_hook_url):
        self.data = {'fields': crm_obj.b24_fields}

        if not web_hook_url.endswith('/'):
            web_hook_url += '/'
        self.web_hook = web_hook_url

    def add_lead(self):
        if settings.DEBUG:
            return 'SKIPPED (DEBUG MODE)'
        url = f'{self.web_hook}{self.LEAD_ADD_METHOD}'
        resp = requests.post(url, json=self.data)
        return resp.text
