from datetime import date, timedelta

from django.db.models import Q
from django.core.mail import EmailMessage
from django.utils.translation import ugettext_lazy as _
from django.template.loader import get_template
from django.conf import settings

from constance import config

from .models import Banner


def notify_advertisers_banner_expires(run_notify=True):
    """
    Sending notifications to advertisers about the extension of their banners.

    If the run_notify flag is set to False, then this function will return only
    QuerySet with a banners objects about which their owners(advertiser) should
    be notified. This is done to be able to use this function in the management command.
    """
    delta = timedelta(days=config.BANNERS_NOTIFY_DAYS_BEFORE_EXPIRE)
    today = date.today()

    banners = Banner.objects.get_active().filter(
        Q(advertiser_email__isnull=False) &
        Q(end_date=today + delta) &
        ~Q(renewal_notice_date=today)
    )

    if not run_notify:
        return banners

    for banner in banners:
        notify_advertiser(banner)


def notify_advertiser(banner):
    """
    Sending email to the advertiser.
    """
    if not banner.advertiser_email:
        return

    subject = _('Banner expiration notification')
    mail_body = get_template(
        'banners/email/notify_advertisers_banner_expires.html').render({
            'banner': banner,
            'config': config})

    mail = EmailMessage(subject, mail_body, config.DEFAULT_FROM_EMAIL,
                        (banner.advertiser_email, ))
    mail.content_subtype = 'html'
    mail.send()

    banner.renewal_notice_date = date.today()
    banner.save(update_fields=['renewal_notice_date'])
