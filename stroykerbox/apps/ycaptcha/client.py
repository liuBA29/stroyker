from logging import getLogger
import json

import requests


logger = getLogger(__name__)


def check_captcha(token: str, remoteip: str, private_key: str) -> bool:
    """проверка токена капчи"""
    resp = requests.get(
        'https://captcha-api.yandex.ru/validate',
        {
            'secret': private_key,
            'token': token,
            'ip': remoteip,
        },
        timeout=1,
    )
    server_output = resp.content.decode()
    if resp.status_code != 200:
        logger.error(
            f'Allow access due to an error: status_code={resp.status_code}; output={server_output}'
        )
        return False
    return json.loads(server_output)['status'] == 'ok'
