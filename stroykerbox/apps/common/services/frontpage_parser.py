from typing import Optional, Any
from html.parser import HTMLParser
from base64 import b64encode
import re


from django.conf import settings
from django.utils.html import strip_tags
import requests


class FrontpageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = list()
        self.html = self._get_frontpage_source()
        self.parsed_data = {}
        self.current_tag = None

    def parse(self):
        if self.html:
            self.parsed_data['h1'] = self.get_tag('h1')
            self.parsed_data['h2'] = self.get_tag('h2')
            self.parsed_data['title'] = self.get_tag('title')
            self.parsed_data['description'] = self.get_meta('description')
            self.parsed_data['keywords'] = self.get_meta('keywords')

    def get_meta(self, name: str) -> Optional[Any]:
        output = []
        matches = re.findall(fr'<meta name="{name}" content="(.*?)".*?>', self.html, re.U | re.I | re.S)  # type: ignore
        for match in matches:
            output.append(strip_tags(match))
        return output

    def get_tag(self, tag: str) -> list:
        output = []
        for match in re.findall(fr'<{tag}.*?>(.*?)</{tag}>', self.html, re.U | re.I | re.S):  # type: ignore
            output.append(strip_tags(match).replace('\r\n', ' '))
        return output

    def _get_frontpage_source(self) -> Optional[str]:
        headers = {
            "Authorization": "Basic {}".format(
                b64encode(bytes('root:root', 'utf-8')).decode("ascii")
            )
        }
        url = settings.BASE_URL
        if url.endswith('local'):
            url = 'http://host.docker.internal'
        try:
            resp = requests.get(url, headers=headers)
        except Exception as e:
            self.errors.append(str(e))
        else:
            if resp.status_code == 200:
                return resp.text

    def check_yandex_metrika(self) -> bool:
        metrika_substring = 'Yandex.Metrika counter -->'
        if self.html:
            return metrika_substring in self.html
        return False
