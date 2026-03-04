import shutil
import os

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from constance.models import Constance
from stroykerbox.apps.slides.models import SliderSet
from stroykerbox.apps.banners.models import BannerMultirowSet


class Command(BaseCommand):

    def handle(self, *args, **options):
        for model in (SliderSet, BannerMultirowSet, Constance):
            model.objects.all().delete()
        # create object in db
        call_command('loaddata', 'default_data.json')

        # copy files from default media (works with 3.8+ only!)
        source = os.path.join(os.path.dirname(
            os.path.dirname(__file__)), '..', 'fixtures/default_media')
        dest = settings.MEDIA_ROOT

        shutil.copytree(source, dest, dirs_exist_ok=True)
