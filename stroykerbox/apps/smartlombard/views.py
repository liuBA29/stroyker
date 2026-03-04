import json
from logging import getLogger

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from django.http import Http404
from django.utils.translation import ugettext as _

from constance import config

from .helper import LombardHelper
from .forms import SLCheckDebtForm


logger = getLogger(__name__)


@csrf_exempt
def lombard_receiver(request):
    logger.debug(
        f'A new request for SmartLombard receiver has been received: {request}')

    if (config.SMARTLOMBARD_ENABLED and
            request.method == 'POST' and 'data' in request.POST):
        try:
            lombard = LombardHelper(request)

            if lombard.is_valid():
                lombard.parse_goods()

            msg = lombard.response_messages

        except Exception as e:
            logger.error(e)
            msg = ['some errors']

        logger.debug(
            f'Response Answer Data: {msg}')

        return HttpResponse(json.dumps(msg))

    return HttpResponseBadRequest()


def online_payment(request):
    if not config.SMARTLOMBARD_PROFILE_ID:
        raise Http404()

    form = SLCheckDebtForm(request.POST or None)
    template = 'smartlombard/online-payment.html'

    context = {'form': form}

    if hasattr(request, 'seo'):
        request.seo.breadcrumbs.append(
            ('', _('Online Payment')))

    if request.method == 'POST':
        if form.is_valid() and isinstance(form.ticket_info, dict):
            context.update(form.ticket_info)
            template = 'smartlombard/online-payment-result.html'

    return render(request, template, context)
