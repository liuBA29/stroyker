from logging import getLogger

from django.conf import settings
from constance import config

import telebot

logger = getLogger('telebot')

PARSEP_MODE = 'HTML'
"""
Allowed tags in HTML-mode:

<b>bold</b>, <strong>bold</strong>
<i>italic</i>, <em>italic</em>
<u>underline</u>, <ins>underline</ins>
<s>strikethrough</s>, <strike>strikethrough</strike>, <del>strikethrough</del>,
<span class="tg-spoiler">spoiler</span>, <tg-spoiler>spoiler</tg-spoiler>,
<a href="http://www.example.com/">inline URL</a>
<a href="tg://user?id=123456789">inline mention of a user</a>
<code>inline fixed-width code</code>
<pre>pre-formatted fixed-width code block</pre>
"""


class StroykerTelebot:
    @staticmethod
    def get_chat_ids_set() -> set | tuple:
        chat_ids = set()
        if config.TELEBOT_CHAT_IDS:
            for i in config.TELEBOT_CHAT_IDS.split(','):
                try:
                    i = int(i.strip())
                except ValueError:
                    continue
                else:
                    chat_ids.add(i)
        elif config.TELEBOT_CHAT_ID:
            chat_ids.add(config.TELEBOT_CHAT_ID)
        return chat_ids

    def __init__(self, **kwargs):
        token = config.TELEBOT_TOKEN or settings.TELEBOT_DEFAULT_TOKEN
        self.chat_ids = None

        if chat_id := kwargs.get('chat_id', None):
            self.chat_ids = (chat_id,)
        else:
            self.chat_ids = self.get_chat_ids_set()  # type: ignore

        parse_mode = kwargs.get('parse_mode') or 'HTML'

        if token and self.chat_ids:
            self.bot = telebot.TeleBot(token, parse_mode=parse_mode)
        else:
            self.bot = None
            logger.error('Telegram bot token or chat_id not set.')

    def send_message(self, msg: str) -> str | bool | None:
        if not self.bot:
            msg = 'Error creating bot'
            logger.error(msg)
            return False

        if settings.DEBUG:
            logger.debug(msg)
        elif self.chat_ids:
            no_errors_flag = True
            for chat_id in self.chat_ids:
                try:
                    response_json = self.bot.send_message(chat_id, msg)
                except Exception as e:
                    no_errors_flag = False
                    logger.exception(e)
                else:
                    logger.debug(response_json)
            return no_errors_flag
