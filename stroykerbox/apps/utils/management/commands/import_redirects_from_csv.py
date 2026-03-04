import os
import csv
import logging


from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache
# from django.db import transaction
from django.db.utils import DatabaseError
from django.contrib.redirects.models import Redirect
from django.conf import settings


logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s')
LOCK_EXPIRE = 60 * 10


def acquire_lock():
    return cache.add("import_redirects", 'true', LOCK_EXPIRE)


def release_lock():
    return cache.delete("import_redirects")


class Command(BaseCommand):
    help = 'Import redirects from csv-file'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--file', action='store', type=str,
                            dest='filename', help='Path to csv-file. Delimiter: ","'),
        parser.add_argument('-l', '--log', action='store',
                            type=str, dest='logfile', help='Path to log-file'),
        parser.add_argument('--change', action='store_true', dest='change',
                            help='Change new_path for existing redirects')

    can_import_settings = True

    def handle(self, *args, **options):
        logfile = options.get('logfile')
        if logfile:
            handler = logging.FileHandler(logfile)
        else:
            handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        if acquire_lock():
            try:
                if not options.get('filename'):
                    raise CommandError(
                        'You must provide path to csv-file. Use -f option.')
                path_to_file = os.path.normpath(options.get('filename'))
                if not os.path.exists(path_to_file):
                    raise CommandError('File not found')
                if os.path.isdir(path_to_file):
                    raise CommandError('%s is a directory' % path_to_file)
                # with open(path_to_file, 'rb') as csvfile:
                with open(path_to_file) as csvfile:
                    try:
                        data = csv.reader(csvfile, delimiter=',', quotechar='"')
                    except csv.Error:
                        mess = 'Incorrect file format'
                        logger.error(mess)
                        raise CommandError(mess)
                    # with transaction.atomic():
                    for i, row in enumerate(data):
                        old_path = row[0]
                        new_path = row[1]
                        if new_path == '':
                            break
                        if not old_path.startswith("/"):
                            mess = 'LINE: %s. Invalid url: %s' % (
                                i + 1, old_path)
                            logger.error(mess)
                            raise Exception(mess)
                        if not new_path.startswith("/"):
                            mess = 'LINE: %s. Invalid url: %s' % (
                                i + 1, new_path)
                            logger.error(mess)

                        if not old_path.endswith("/"):
                            old_path += '/'
                        try:
                            redirect, created = Redirect.objects.get_or_create(
                                site_id=settings.SITE_ID, old_path=old_path)
                            redirect.new_path = new_path
                            redirect.save()
                        except DatabaseError as e:
                            mess = (f'Error in transaction. '
                                    f'OldURL:{redirect.old_path}, NewURL:{redirect.new_path}\n '
                                    f'MSG: {e}')
                            logger.error(mess)
                            # raise
                            continue
                logger.info('Import completed successfully')
            except: # noqa
                pass
            finally:
                release_lock()
        else:
            logger.error(
                'Redirects is already being imported. Please repeat later')
