import subprocess
import re

from django.conf import settings


def get_commits_count(day_ago=30):
    command = ['git', 'rev-list', 'master',
               '--count', f'--since={day_ago}.day']
    try:
        commits_count = subprocess.run(
            command, stdout=subprocess.PIPE, text=True)
    except Exception:
        return ''
    return re.sub("[^0-9]", "", commits_count.stdout)


def get_version(major_version_number=None, after_date=None):
    command = ['git', 'rev-list', 'master', '--count']
    if after_date:
        command.append(f'--after={after_date}')
    try:
        commits_count = subprocess.run(
            command, stdout=subprocess.PIPE, text=True)
    except Exception:
        return ''

    minor_num = re.sub("[^0-9]", "", commits_count.stdout)

    return f'{major_version_number or 0}.{minor_num}'


__version__ = get_version(getattr(settings, 'PROJECT_MAJOR_VERSION', 1),
                          getattr(settings, 'PROJECT_MINOR_VERSION_AFTER_DATE', '01.01.2021'))
