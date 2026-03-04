from django.core.management.base import BaseCommand

from stroykerbox.apps.banners import tasks


class Command(BaseCommand):
    help = 'Sending notifications to advertisers about the extension of their banners.'  # noqa: ignore=B001

    def handle(self, *args, **options):
        banners = tasks.notify_advertisers_banner_expires(False)
        if banners:
            for banner in banners:
                tasks.notify_advertiser(banner)
                self.stdout.write(f'Banner "{banner.name}": a notification to '
                                  f'the banner owner was sent to {banner.advertiser_email}.')
        else:
            self.stdout.write('There are no banners requiring notifications.')
