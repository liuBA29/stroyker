import simplejson as json

from django.views import View
from django.views.generic import TemplateView
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.translation import ugettext as _
from django.contrib.humanize.templatetags.humanize import intcomma
from django.http.response import HttpResponse, HttpResponseBadRequest
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.db import IntegrityError
from stroykerbox.settings.constants import YOOKASSA

# from django.contrib.admin.views.decorators import staff_member_required
from pytils.numeral import choose_plural
from constance import config
from stroykerbox.apps.utils.constance_helpers import get_config_list

from stroykerbox.apps.catalog.models import Product, Stock
from stroykerbox.apps.catalog.templatetags.catalog_tags import price_format
from stroykerbox.apps.commerce import tasks, cart as cart_tools, utils
from stroykerbox.settings.constants import INVOICING

from .forms import (
    OrderForm,
    SimpleOrderForm,
    create_delivery_forms,
    DeliveryCalculatorForm,
    OrderStatusForm,
)
from .models import (
    DeliveryCar,
    OrderExtraField,
    OrderExtraFieldValue,
    TransportCompany,
    Order,
    OrderContactData,
    YookassaData,
    BINDED_PICKUP_DELIVERY,
    BINDED_ADDRESS_DELIVERY,
    BINDED_TK_DELIVERY,
    BINDED_ALL,
    BINDED_PAYMENT_0,
    BINDED_PAYMENT_1,
    BINDED_PAYMENT_2,
    BINDED_PAYMENT_3,
    BINDED_PAYMENT_4,
    BINDED_PAYMENT_5,
)
from .payment import Payment, yookassa_payment
from .signals import new_order_created


DESIRED_DELIVERY_OPTION_TEXT = _('Desired delivery option is: ')
DESIRED_PAYMENT_OPTION_TEXT = _('Desired payment option is: ')


def add_to_cart(request, product_pk):
    product = get_object_or_404(Product, pk=product_pk)
    cart = cart_tools.Cart.from_request(request)

    response = {'result': 'success'}
    try:
        qty = int(request.GET.get('qty', 1))
    except ValueError:
        qty = 1

    try:
        cart.add_product(product, qty)
    except cart_tools.ItemUnavailable:
        response.update(
            {'result': 'error', 'message': _('Product is not available at this moment')}
        )
    except cart_tools.WrongQuantity as e:
        response.update({'result': 'error', 'message': str(e)})
    else:
        response.update(
            {
                'total_price': intcomma(cart.total_price),
                'count': intcomma(len(cart)),
                'total_count': intcomma(cart.total_count),
                'message': _('Product was added to the cart'),
                'word': choose_plural(len(cart), _('product,products,products')),
                'events_log': cart.events_log,
            }
        )
        cart.save_to_session(request.session)

    if not request.is_ajax():
        msg = response['message']
        if response['result'] == 'error':
            messages.error(request, msg)
        else:
            messages.info(request, msg)

        ref = request.META.get('HTTP_REFERER')
        redirect_url = ref if ref and ref.startswith(settings.BASE_URL) else '/'

        return redirect(redirect_url)

    return HttpResponse(json.dumps(response), content_type='application/json')


def cart_simple_mode(request):
    cart = cart_tools.Cart.from_request(request)

    order = None

    if request.method == 'POST':
        form = SimpleOrderForm(request.POST)

        if form.is_valid():
            order = form.save(commit=False)

            payment_id = form.cleaned_data.get('payment_variant')
            delivery = form.cleaned_data.get('delivery_variant')
            pickup_point = form.cleaned_data.get('pickup_point')
            print(pickup_point, delivery)
            # creating a wishes in addition to order comments
            if payment_id or delivery:
                comment_parts = []
                if order.comment:
                    comment_parts.append(order.comment)
                if delivery:
                    order.delivery_cart_simple_mode = delivery.lower()
                    if delivery.lower() == 'самовывоз' and pickup_point:
                        order.delivery_cart_simple_mode += (
                            f';{pickup_point.name.lower()}'
                        )
                if payment_id and payment_id.isnumeric():
                    order.payment_method = int(payment_id)

            order.location = cart.location or None
            order.from_cart = True
            order.save()

            # creating a contact data object from form values
            contact_data = {}
            for f in ('name', 'email', 'phone'):
                contact_data[f] = form.cleaned_data.get(f)
            OrderContactData.objects.create(order=order, **contact_data)

            # creating orderextrafields
            for field in OrderExtraField.objects.all():
                field_value = form.cleaned_data.get(f'extra_{field.id}')
                if field_value:  # Faqat to'ldirilgan maydonlarni saqlaymiz
                    OrderExtraFieldValue.objects.create(
                        order=order, field=field, value=field_value
                    )

            cart.order = order
            order.populate_from_cart(cart)
            order.save()
            cart.save_to_session(request.session)

            if order.payment_method == YOOKASSA:
                return redirect(yookassa_payment.create(order))

            return redirect(reverse('cart:success'))
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'name': request.user.name,
                'email': request.user.email,
                'phone': request.user.phone,
            }
        form = SimpleOrderForm(initial=initial_data)

    stocks = Stock.objects.filter(pickup_point=True)

    extra_fields = OrderExtraField.objects.all()
    for field in extra_fields:
        if field.field_type == 'select' and field.choices:
            field.split_choices = field.choices.split(',')

    if hasattr(request, 'seo'):
        request.seo.breadcrumbs.append((request.path, _('Cart')))
        request.seo.title.append(_('Cart'))

    return render(
        request,
        'cart/cart-page-simple-mode.html',
        {
            'cart': cart,
            'form': form,
            'order': order,
            'stocks': stocks,
            'extra_fields': extra_fields,
        },
    )


def cart(request):
    if hasattr(request, 'seo'):
        request.seo.title.append(_('Cart'))

    if config.SIMPLE_CART_MODE:
        return cart_simple_mode(request)

    cart = cart_tools.Cart.from_request(request)

    if not getattr(cart, 'products', None):
        return render(request, 'cart/empty-cart-page.html')

    if request.method == 'POST':
        # Need a copy of the POST dict as it's going to be modified.
        cart.save_to_session(request.session)

    return render(request, 'cart/cart-page.html', {'cart': cart})


def update_product_quantity(request, product_pk):
    product = get_object_or_404(Product, pk=product_pk)
    cart = cart_tools.Cart.from_request(request)
    quantity = cart.products[product.pk]
    response = {
        'result': 'success',
        'message': _('Product quantity updated'),
    }
    wrong_qty_response = {'result': 'error', 'message': _('Invalid quantity')}
    request_qty = request.GET.get('qty', None)
    if request_qty:
        try:
            quantity = int(request_qty)
        except ValueError:
            response = wrong_qty_response
    elif request.GET.get('q') == 'up':
        quantity += 1
    elif request.GET.get('q') == 'down':
        quantity -= 1
    else:
        response = wrong_qty_response

    try:
        cart.update_quantity(product, quantity)
        cart.save_to_session(request.session)
    except cart_tools.WrongQuantity as e:
        response.update({'result': 'error', 'message': str(e)})

    response.update(
        {
            'quantity': quantity,
            'product_price_total': price_format(
                cart.product_cart_price(product) * quantity
            ),
            'base_price': price_format(cart.base_price),
            'total_price': price_format(cart.total_price),
            'total_weight': cart.total_weight,
            'total_volume': cart.total_volume,
            'count': cart.total_count,
        }
    )

    return HttpResponse(json.dumps(response), content_type='application/json')


def remove_from_cart(request, product_pk):
    product = get_object_or_404(Product, pk=product_pk)
    cart = cart_tools.Cart.from_request(request)
    try:
        cart.remove_product(product)
        cart.save_to_session(request.session)
    except cart_tools.ProductNotFound as e:
        return HttpResponseBadRequest(e)
    return redirect(reverse('cart:cart'))


@cart_tools.not_empty_cart_required()
def cart_delivery(request):
    if config.SIMPLE_CART_MODE:
        return redirect('cart:cart')

    if hasattr(request, 'seo'):
        request.seo.breadcrumbs.append((reverse('cart:cart'), _('Cart')))
        request.seo.breadcrumbs.append((request.path, _('Delivery')))

    cart = cart_tools.Cart.from_request(request)

    order_instance = None
    delivery_instance = None
    delivery_type_class = None

    if cart.order is not None and cart.order.delivery:
        order_instance = cart.order
        delivery_instance = order_instance.delivery
        delivery_type_class = delivery_instance.__class__

    products = list(iter(cart))
    common_extra_fields = []
    delivery_extra_fields = []

    if request.method == 'POST':
        form = OrderForm(data=request.POST, instance=order_instance)
        if form.is_valid():
            delivery_forms, delivery_form = create_delivery_forms(
                form.cleaned_data.get('delivery_type').model_class(),
                location=cart.location,
                products=products,
                data=request.POST,
                instance=delivery_instance,
            )
            if delivery_form.is_valid():
                delivery = delivery_form.save()
                order = form.save(commit=False)
                order.delivery = delivery
                order.location = cart.location or None
                order.from_cart = True
                order.save()
                cart.order = order
                # populate order data from cart
                order.populate_from_cart(cart)
                order.save()
                cart.save_to_session(request.session)
                return redirect(reverse('cart:payment'))
        else:
            delivery_forms, delivery_form = create_delivery_forms(
                delivery_type_class,
                products=products,
                location=cart.location,
                data=request.POST,
                instance=delivery_instance,
                request=request,
            )
    else:
        delivery_forms_initial_data = None
        if request.user.is_authenticated:
            delivery_forms_initial_data = {
                'name': request.user.name,
                'email': request.user.email,
                'phone': request.user.phone,
            }

        form = OrderForm(
            instance=order_instance,
            initial=OrderForm.get_initial() if order_instance is None else None,
        )
        delivery_forms, delivery_form = create_delivery_forms(
            delivery_type_class,
            products=products,
            location=cart.location,
            initial=delivery_forms_initial_data,
            instance=delivery_instance,
        )

        delivery_config_map: dict[str, int] = {
            'PickUpDelivery': BINDED_PICKUP_DELIVERY,
            'ToAddressDelivery': BINDED_ADDRESS_DELIVERY,
            'ToTCDelivery': BINDED_TK_DELIVERY,
        }

        delivery_extra_fields_filter = {
            'binded_to__in': [delivery_config_map[k] for k in get_config_list('DELIVERY_METHODS')]
        }
        common_extra_fields_filter = {
            'binded_to__in': [
                BINDED_ALL,
            ]
        }

        delivery_extra_fields = OrderExtraField.objects.filter(
            **delivery_extra_fields_filter
        ).order_by('position')
        for field in delivery_extra_fields:
            if field.field_type == 'select' and field.choices:
                field.split_choices = field.choices.split(',')

        common_extra_fields = OrderExtraField.objects.filter(
            **common_extra_fields_filter
        ).order_by('position')
        for field in common_extra_fields:
            if field.field_type == 'select' and field.choices:
                field.split_choices = field.choices.split(',')

    return render(
        request,
        'cart/delivery.html',
        {
            'cart': cart,
            'config': config,
            'delivery_forms': delivery_forms,
            'common_extra_fields': common_extra_fields,
            'delivery_extra_fields': delivery_extra_fields,
            'form': form,
            'map_center_latitude': (
                cart.location.latitude
                if cart.location
                else config.YAMAP_DEFAULT_CENTER_LATITUDE
            ),
            'map_center_longitude': (
                cart.location.longitude
                if cart.location
                else config.YAMAP_DEFAULT_CENTER_LONGITUDE
            ),
        },
    )


@cart_tools.not_empty_cart_required()
def cart_payment(request):
    if hasattr(request, 'seo'):
        request.seo.breadcrumbs.append((reverse('cart:cart'), _('Cart')))
        request.seo.breadcrumbs.append((reverse('cart:delivery'), _('Delivery')))
        request.seo.breadcrumbs.append((request.path, _('Payment')))

    cart = cart_tools.Cart.from_request(request)
    if not cart.order or not cart.order.delivery:
        if config.SIMPLE_CART_MODE:
            return redirect('cart:cart')
        return redirect('cart:delivery')

    payment = Payment(cart.order)
    if request.method == 'POST':
        form = payment.get_payment_select_form(data=request.POST)
        if form.is_valid():
            try:
                payment_method = int(request.POST.get('payment_method'))
            except TypeError:
                raise Http404()
            else:
                return payment.process_payment(request, payment_method)

    form = payment.get_payment_select_form()

    payment_config_map: dict[str, int] = {
        '0': BINDED_PAYMENT_0,
        '1': BINDED_PAYMENT_1,
        '2': BINDED_PAYMENT_2,
        '3': BINDED_PAYMENT_3,
        '4': BINDED_PAYMENT_4,
        '5': BINDED_PAYMENT_5,
    }

    payment_extra_fields_filter = {
        'binded_to__in': [payment_config_map[k] for k in get_config_list('PAYMENT_METHODS')]
    }

    payment_extra_fields = OrderExtraField.objects.filter(
        **payment_extra_fields_filter
    ).order_by('position')
    for field in payment_extra_fields:
        if field.field_type == 'select' and field.choices:
            field.split_choices = field.choices.split(',')

    ctx = {
        'cart': cart,
        'order': cart.order,
        'form': form,
        'extra_fields': payment_extra_fields,
    }

    return render(request, 'cart/payment.html', context=ctx)


@cart_tools.not_empty_cart_required()
def cart_confirm(request):
    if hasattr(request, 'seo'):
        request.seo.breadcrumbs.append((reverse('cart:cart'), _('Cart')))
        request.seo.breadcrumbs.append((reverse('cart:delivery'), _('Delivery')))
        request.seo.breadcrumbs.append((reverse('cart:payment'), _('Payment')))

    cart = cart_tools.Cart.from_request(request)
    if config.SIMPLE_CART_MODE and not (
        cart.order and cart.order.payment_method and cart.order.delivery
    ):
        return redirect('cart:cart')
    elif not cart.order:
        return redirect('cart:delivery')
    elif cart.order.payment_method is None:
        return redirect('cart:payment')
    return render(
        request,
        'cart/confirm.html',
        {
            'cart': cart,
            'order': cart.order.as_dict,
        },
    )


@cart_tools.not_empty_cart_required()
def cart_success(request):
    if hasattr(request, 'seo'):
        request.seo.breadcrumbs.append((reverse('cart:cart'), _('Cart')))
        if not config.SIMPLE_CART_MODE:
            request.seo.breadcrumbs.append((reverse('cart:delivery'), _('Delivery')))
            request.seo.breadcrumbs.append((reverse('cart:payment'), _('Payment')))
        request.seo.breadcrumbs.append((request.path, _('Successful order')))

    cart = cart_tools.Cart.from_request(request)
    if not cart.order:
        if config.SIMPLE_CART_MODE:
            return redirect('cart:cart')
        return redirect('cart:delivery')

    order = cart.order
    if order.payment_method == YOOKASSA:
        if order.yookassa_status in (
            None,
            Order.YOOKASSA_PENDING,
            Order.YOOKASSA_PAYMENT_STATUS_CHOICES,
        ):
            yookassa_payment.check_status(order)

        # независимо от статуса платежа, сохраняем заказ https://redmine.fancymedia.ru/issues/12255#note-5
        if order.yookassa_status == Order.YOOKASSA_SUCCEEDED:
            order.is_paid = True
            order.save()

    # # reset the cart
    cart.reset()
    cart.save_to_session(request.session)

    order.status = 'new'

    # If the order user is an anonymous user, then upon completion of the
    # order we create a new account for him.
    # If an error occurs when creating a new account due to data matching with
    # an existing user, then a new account is not needed.
    new_account = all((config.WHITETHEME_SHOW_LK_LINKS, not hasattr(order, 'user')))

    try:
        order.save()
    except ValidationError as e:
        # The order has been modified by manager or cancelled automatically. Show the error message to user.
        return render(request, 'cart/failed.html', {'order': order, 'error': e})
    except IntegrityError:
        new_account = False

    # send a custom signal that a completed order
    # has been created with the status "new"
    new_order_created.send(sender=order.__class__, order=order)

    if order.from_cart:
        # Notify only for a cart orders.
        tasks.new_order_notify_customer.delay(order.pk)
    if new_account:
        utils.new_customer_order_registration(order)

    tasks.new_order_notify_manager.delay(order.pk)

    invoicing = all(
        (
            order.payment_method == INVOICING,
            bool(config.INVOICE_PDF_AUTOGENERATION),
            bool(order.user or config.INVOICE_PDF_ANON_ALLOWED),
        )
    )
    template = (
        'cart/success.html'
        if not config.SIMPLE_CART_MODE
        else 'cart/success-simple-mode.html'
    )

    return render(request, template, {'order': order, 'invoicing': invoicing})


class CartFailed(TemplateView):
    template_name = 'cart/failed.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = cart_tools.Cart.from_request(self.request).order
        if order is None:
            raise Http404
        context['order'] = order
        return context


class AjaxGetBase(View):
    def dispatch(self, request, *args, **kwargs):
        self.cart = cart_tools.Cart.from_request(request)
        return super().dispatch(request, *args, **kwargs)

    def render_to_json_response(self, context, **kwargs):
        return JsonResponse(context, **kwargs)

    def get(self, request, *args, **kwargs):
        raise Http404()


class AjaxGetDeliveryToAddressCost(AjaxGetBase):
    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            try:
                route_length_km = int(request.GET.get('route_length_km', 0))
                car_pk = int(request.GET.get('car_pk'))
            except ValueError:
                pass
            else:
                if self.cart is not None:
                    try:
                        car = DeliveryCar.objects.get(pk=car_pk)
                    except DeliveryCar.DoesNotExist:
                        raise Http404

                    delivery_cost = 0
                    if route_length_km > 0:
                        delivery_cost = round(route_length_km * car.cost_km)
                        if car.store_start_cost:
                            delivery_cost += car.store_start_cost

                    cost_with_delivery = self.cart.total_price + delivery_cost
                    return self.render_to_json_response(
                        {
                            'success': True,
                            'delivery_cost': delivery_cost,
                            'cost_with_delivery': cost_with_delivery,
                        }
                    )
            return self.render_to_json_response({'success': False})
        super().get(self, request, *args, **kwargs)


class AjaxGetDeliveryToTCCost(AjaxGetBase):
    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            try:
                tc_pk = int(request.GET.get('tc_pk'))
            except ValueError:
                pass
            else:
                try:
                    tc = TransportCompany.objects.get(pk=tc_pk)
                except TransportCompany.DoesNotExist:
                    raise Http404

                delivery_cost = tc.delivery_price
                cost_with_delivery = self.cart.total_price + delivery_cost
                return self.render_to_json_response(
                    {
                        'success': True,
                        'delivery_cost': delivery_cost,
                        'cost_with_delivery': cost_with_delivery,
                    }
                )
            return self.render_to_json_response({'success': False})
        super().get(self, request, *args, **kwargs)


def check_invoice_pdf_perms(request, order):
    if request.user.is_staff:
        return True

    if order.payment_method != INVOICING or not config.INVOICE_PDF_AUTOGENERATION:
        return False

    if order.user and request.user.pk == order.user.pk:
        return True

    return config.INVOICE_PDF_ANON_ALLOWED


def order_invoice_pdf(request, order_pk):
    """
    Url to generate a billing invoice in pdf for a specific order.
    For staff only.
    """
    from io import BytesIO
    from weasyprint import HTML, CSS
    from django.template.loader import render_to_string

    order = get_object_or_404(Order, pk=order_pk, payment_method=INVOICING)

    if not check_invoice_pdf_perms(request, order):
        raise PermissionDenied()

    customer_name = None
    if order.user:
        customer_name = order.user.company or order.user.name or order.user.email
    elif hasattr(order, 'ordercontactdata'):
        customer_name = order.ordercontactdata.name

    html = render_to_string(
        'commerce/include/order-invoice-pdf.html',
        {
            'config': config,
            'order': order,
            'customer_name': customer_name or '',
        },
    )
    result = BytesIO()
    HTML(string=html).write_pdf(result, stylesheets=[CSS(settings.INVOICE_CSS_PATH)])

    response = HttpResponse(content_type='application/pdf;')
    response['Content-Disposition'] = 'inline; filename=invoicing-order-{}.pdf'.format(
        order_pk
    )
    response['Content-Transfer-Encoding'] = 'binary'
    response.write(result.getvalue())
    return response


def order_invoice_html(request, order_pk):
    """
    Url to generate a billing invoice in html for a specific order.
    For staff only and test purposes.
    """

    order = get_object_or_404(Order, pk=order_pk)

    customer_name = None
    if order.user:
        customer_name = order.user.company or order.user.name or order.user.email
    elif hasattr(order, 'ordercontactdata'):
        customer_name = order.ordercontactdata.name

    if not request.user.is_staff and request.user is not order.user:
        raise PermissionDenied()

    return render(
        request,
        'commerce/include/order-invoice-html.html',
        {
            'config': config,
            'order': order,
            'customer_name': customer_name or '',
        },
    )


def delivery_calculator(request):
    form = DeliveryCalculatorForm(location=request.location)
    if hasattr(request, 'seo'):
        title = _('Delivery Calculator')
        request.seo.breadcrumbs.append((request.path, title))
        request.seo.title.append(title)

    return render(
        request,
        'cart/delivery_calculator.html',
        {
            'form': form,
            'config': config,
            'map_center_latitude': (
                request.location.latitude
                if request.location
                else config.YAMAP_DEFAULT_CENTER_LATITUDE
            ),
            'map_center_longitude': (
                request.location.longitude
                if request.location
                else config.YAMAP_DEFAULT_CENTER_LONGITUDE
            ),
        },
    )


def status(request):
    form = OrderStatusForm(request.GET or None)
    if form.is_valid():
        order = form.cleaned_data['order']
        context = {'order': order}
        if config.SIMPLE_CART_MODE:
            context['delivery_text'] = order.delivery_cart_simple_mode
        return render(request, 'commerce/status.html', context)
    return render(request, 'commerce/form_status.html', {'form': form})


def ajax_add_to_cart_related(request):
    products = request.POST.get('products')
    if not request.is_ajax() or not products:
        return HttpResponseBadRequest()

    errors = []
    response = {}

    products = json.loads(products)
    cart = cart_tools.Cart.from_request(request)
    successed = 0

    for pk, qty in products.items():
        if qty <= 0:
            continue
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            continue
        try:
            cart.add_product(product, qty)
        except cart_tools.ItemUnavailable:
            err_msg = _(
                'Товар "%(product_name)s" в настроящий момент не доступен к продаже.'
            ) % {'product_name': product.name}
            errors.append(err_msg)
        except cart_tools.WrongQuantity as e:
            errors.append(str(e))
        else:
            successed += 1

    cart.save_to_session(request.session)

    if successed:
        response['success'] = _('Товары успешно добавлены в Вашу корзину.')
        response['count'] = successed

    if errors:
        response['errors'] = '\n'.join(errors)

    return JsonResponse(response)


def yookassa_confirm(request, slug):
    yoo_data = get_object_or_404(YookassaData, slug=slug)
    order = yoo_data.order
    if order.payment_method == YOOKASSA:
        if order.yookassa_status in (Order.YOOKASSA_PENDING, Order.WAITING_FOR_CAPTURE):
            yookassa_payment.check_status(order)
        # независимо от статуса платежа, сохраняем заказ https://redmine.fancymedia.ru/issues/12255#note-5
        if order.yookassa_status == Order.YOOKASSA_SUCCEEDED:
            order.is_paid = True
            order.save()
        elif config.YOOKASSA_NOT_ORDER_WITHOUT_PAYMENT:
            messages.add_message(
                request, messages.ERROR, _('Ошибка оплаты, попробуйте еще раз')
            )
            return redirect('cart:failed')
    return redirect('cart:success')
