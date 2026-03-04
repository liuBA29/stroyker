import re
import json
from logging import getLogger

from constance import config

from .models import NovofonCall, CALL_TYPE_OUTGOING, CALL_TYPE_INCOMING
from .novofon import NovofonAPI

logger = getLogger(__name__)


DATETIME_STRING_FORMAT = '%Y-%m-%d %H:%M:%S'


def novofon_enabled():
    return all((config.NOVOFON_KEY,
                config.NOVOFON_SECRET,
                config.NOVOFON_PHONES))


class Novofon:
    STATS_METHOD = '/v1/statistics/'

    def __init__(self):
        self.api = NovofonAPI(key=config.NOVOFON_KEY,
                              secret=config.NOVOFON_SECRET)
        self.phones_list = self.get_phones_list()
        logger.debug(f'Site Phones (from settings): {self.phones_list}')

    @staticmethod
    def get_phones_list():
        if config.NOVOFON_PHONES:
            sep = ',' if ',' in config.NOVOFON_PHONES else None
            return [re.sub('[^0-9]', '', phone) for phone in config.NOVOFON_PHONES.split(sep)]
        return []

    def get_stats(self):
        params = {}
        if NovofonCall.objects.exists():
            last_date = NovofonCall.objects.order_by(
                '-call_dt').first().call_dt
            params['start'] = last_date.strftime(DATETIME_STRING_FORMAT)

        logger.debug(f'Trying to get statistics.\nParams: {params}')

        return self.api.call(self.STATS_METHOD, params)

    def process_stats(self):
        stats_data = json.loads(self.get_stats())
        if stats_data.get('status') != 'success':
            logger.error(stats_data)
            return f'Errors:\n{stats_data}'
        else:
            logger.info(stats_data)

        for call in stats_data.get('stats', []):
            id = call.get('id', 0)
            if NovofonCall.objects.filter(id=id).exists():
                continue

            number_to = str(call.get('to', ''))
            number_from = str(call.get('from', ''))

            if number_from in self.phones_list:
                call_type = CALL_TYPE_OUTGOING
            elif number_to in self.phones_list:
                call_type = CALL_TYPE_INCOMING
            else:
                continue

            obj = NovofonCall(
                id=id,
                call_dt=call.get('callstart'),
                sip=call.get('sip'),
                number_from=number_from,
                number_to=number_to,
                disposition=call.get('disposition'),
                billseconds=call.get('billseconds'),
                call_type=call_type
            )

            try:
                obj.save()
            except Exception as e:
                logger.error(e)
            else:
                logger.debug(f'Data received for a new call with ID {obj.id}')
