from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib.sites.models import Site
from django.core.mail import send_mail
from django.template.loader import get_template
from django.utils.html import strip_tags

from django_rq import job
from constance import config


@job
def send_review_notification_email_manager(review):
    # send email notification to manager
    body = get_template('reviews/email/review_notification_manager.html')
    site = Site.objects.get_current()
    context = {'review': review, 'site': site}
    recipient_list = [x[1] for x in settings.MANAGERS]
    send_mail(subject=_('New Product Review Alert'), message=strip_tags(body.render(context)),
              html_message=body.render(context), from_email=config.DEFAULT_FROM_EMAIL,
              recipient_list=recipient_list)
