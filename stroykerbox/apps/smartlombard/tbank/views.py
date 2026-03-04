from django.views.decorators.http import require_http_methods
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.http import Http404, HttpResponseBadRequest, HttpResponse
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache

from constance import config

from .forms import SLTicketInfoForm, TBankPaymentForm
from .services.tbank_api import TBankAPI
from .models import TBankPayment

SMARTLOMBARD_TBANK_CACHE_KEY = 'smarlombard_tbank_ticket_data'
SMARTLOMBARD_TBANK_CACHE_TIMEOUT = 60 * 60  # час


@staff_member_required
def tbank_prepayment(request):
    if not config.SMARTLOMBARD_PROFILE_ID:
        raise Http404()

    form = SLTicketInfoForm(request.POST or None)

    context = {'form': form}

    if hasattr(request, 'seo'):
        request.seo.breadcrumbs.append(('', 'Т-Банк'))
        request.seo.title.append('Т-Банк')

    if request.method == 'POST':
        if form.is_valid() and isinstance(form.ticket_info, dict):
            cache_key = (
                f'{SMARTLOMBARD_TBANK_CACHE_KEY}:{form.ticket_info["ticket_number"]}'
            )
            cache.set(cache_key, form.ticket_info, SMARTLOMBARD_TBANK_CACHE_TIMEOUT)
            return redirect(
                reverse(
                    'tbank:payment',
                    kwargs={'ticket_number': form.ticket_info['ticket_number']},
                )
            )

    template = 'smartlombard/tbank/tbank-prepayment.html'

    return render(request, template, context)


@staff_member_required
def tbank_payment(request, ticket_number: str):
    template = 'smartlombard/tbank/tbank-payment.html'
    cache_key = f'{SMARTLOMBARD_TBANK_CACHE_KEY}:{ticket_number}'
    debt = None
    ticket_info = cache.get(cache_key)

    if isinstance(ticket_info, dict):
        debt = ticket_info.get('debt')
    if not debt:
        messages.add_message(
            request,
            messages.ERROR,
            (
                f'Задолженность по залогому билету {ticket_number} неизвестна или отсутствует. '
                'Проверьте данные билета еще раз.'
            ),
        )
        return redirect(reverse('tbank:prepayment'))

    context = {}

    if request.method == 'POST':
        form = TBankPaymentForm(request.POST)
        if form.is_valid():
            api = TBankAPI()

            new_order_data = api.payment_init(
                order_id=form.cleaned_data['ticket_number'],
                amount=form.cleaned_data['amount'],
            )
            if all((new_order_data.get('Success'), new_order_data.get('PaymentURL'))):
                payment = TBankPayment.objects.create(
                    payment_id=new_order_data['PaymentId'],
                    order_id=new_order_data['OrderId'],
                    amount=new_order_data['Amount'],
                    payment_url=new_order_data['PaymentURL'],
                    status=new_order_data['Status'],
                )
                payment.write_to_log(new_order_data)
                context['payment'] = payment
                cache.delete(cache_key)
            else:
                messages.add_message(
                    request,
                    messages.ERROR,
                    f'Ошибка инициализации платежа. Данные с сервера T-Банка: {new_order_data}',
                )
    else:
        form = TBankPaymentForm(
            initial={'amount': int(debt * 100), 'ticket_number': ticket_number}
        )

    context.update({'ticket_info': ticket_info, 'form': form})

    if hasattr(request, 'seo'):
        request.seo.breadcrumbs.append(
            (reverse('tbank:prepayment'), 'Проверка залогового билета')
        )
        request.seo.breadcrumbs.append((None, 'Создание платежа'))
        request.seo.title.append('Т-Банк - Создание платежа')

    return render(request, template, context)


@csrf_exempt
@require_http_methods(('POST',))
def tbank_notify(request):
    api = TBankAPI()
    if data := api.get_request_data(request):
        try:
            payment = TBankPayment.objects.get(pk=data.get('PaymentId'))
        except TBankPayment.DoesNotExist:
            return HttpResponseBadRequest()
        payment.update_payment_status(data)
        return HttpResponse('OK')
    return HttpResponseBadRequest()
