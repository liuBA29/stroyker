import re

from django import forms
from django.utils.safestring import mark_safe
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _
from django.conf import settings

from stroykerbox.settings.constants import INVOICING, PAYMENT_METHODS_CHOICES
from stroykerbox.apps.catalog.models import Stock
from stroykerbox.apps.commerce import models
from stroykerbox.apps.utils.forms import ReCaptchaFormMixin
from stroykerbox.apps.utils.constance_helpers import get_config_list
from constance import config

from .models import Order, OrderExtraField, TransportCompany
from .utils import get_payment_methods_names


class OrderFormBase(ReCaptchaFormMixin, forms.ModelForm):
    def captcha_enabled(self):
        if super().captcha_enabled():
            return not settings.DEBUG and config.RECAPTCHA_CART_FORM


class OrderForm(OrderFormBase):

    class Meta:
        model = models.Order
        fields = ('delivery_type', 'comment')

        widgets = {
            'delivery_type': forms.RadioSelect(),
            'comment': forms.Textarea(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(OrderForm, self).__init__(*args, **kwargs)
        content_types = [
            ContentType.objects.get_for_model(m)
            for m in models.Order.DELIVERY_MODELS
            if m.__name__ in get_config_list('DELIVERY_METHODS')
        ]
        self.fields['delivery_type'].choices = [
            (t.pk, t.model_class().get_display_name()) for t in content_types
        ]

    @staticmethod
    def get_initial():
        return {
            'delivery_type': ContentType.objects.get_for_model(models.PickUpDelivery).pk
        }


class SimpleOrderForm(OrderFormBase):
    name = forms.CharField(
        label=_('Contact Name'), max_length=60, widget=forms.TextInput()
    )
    phone = forms.CharField(label=_('Phone'), max_length=18, widget=forms.TextInput())
    email = forms.EmailField(label=_('E-mail'), max_length=60, widget=forms.TextInput())
    delivery_variant = forms.ChoiceField(
        widget=forms.RadioSelect(attrs={'class': 'new-radio__input'}), required=False
    )
    payment_variant = forms.ChoiceField(
        widget=forms.RadioSelect(attrs={'class': 'new-radio__input'}), required=False
    )
    pickup_point = forms.ModelChoiceField(
        queryset=Stock.objects.filter(pickup_point=True),  # Barcha omborlarni olish
        widget=forms.RadioSelect(attrs={'class': 'cart-radio'}),
        required=False,
    )

    class Meta:
        model = models.Order
        fields = ('comment', 'pickup_point')

        widgets = {'comment': forms.Textarea(attrs={'class': 'form-control'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        content_types = [
            ContentType.objects.get_for_model(m)
            for m in models.Order.DELIVERY_MODELS
            if m.__name__ in get_config_list('DELIVERY_METHODS')
        ]
        delivery_variant_choices = []
        payment_mapping = {
            settings.DELIVERY_PICKUP_MODEL_NAME.lower(): get_config_list('DELIVERY_PICUP_PAYMENT_METHODS'),
            settings.DELIVERY_TOADDRESS_MODEL_NAME.lower(): get_config_list('DELIVERY_TOADDRESS_PAYMENT_METHODS'),
            settings.DELIVERY_TOTC_MODEL_NAME.lower(): get_config_list('DELIVERY_TOTC_PAYMENT_METHODS'),
        }
        self.delivery_payment_mapping = {}
        for t in content_types:
            name = t.model_class().get_display_name()
            delivery_variant_choices.append((name, name))
            if t.model in payment_mapping:
                self.delivery_payment_mapping[str(name)] = payment_mapping[t.model]
        self.fields['delivery_variant'].choices = delivery_variant_choices
        # https://redmine.fancymedia.ru/issues/12913
        if delivery_variant_choices:
            # https://redmine.nastroyker.ru/issues/13844
            self.initial['delivery_variant'] = delivery_variant_choices[0][0]

        payment_names_dict = get_payment_methods_names()
        payment_variant_choices = [
            (key, payment_names_dict[key])
            for key, name in PAYMENT_METHODS_CHOICES
            if str(key) in get_config_list('PAYMENT_METHODS')
        ]
        if payment_variant_choices:
            self.fields['payment_variant'].choices = payment_variant_choices
            # https://redmine.fancymedia.ru/issues/12913
            self.initial['payment_variant'] = payment_variant_choices[0][0]

        self.extra_fields = OrderExtraField.objects.all()

        # Har bir extra field uchun formaga qo'shish
        for field in self.extra_fields:
            field_name = f"extra_{field.id}"

            if field.field_type == 'text':
                self.fields[field_name] = forms.CharField(
                    label=field.label,
                    max_length=200,
                    required=field.required,
                    widget=forms.TextInput(attrs={"class": field.css_class}),
                )
            elif field.field_type == 'textarea':
                self.fields[field_name] = forms.CharField(
                    label=field.label,
                    required=field.required,
                    widget=forms.Textarea(attrs={"class": field.css_class}),
                )
            elif field.field_type == 'select':
                choices = [
                    (choice.strip(), choice.strip())
                    for choice in field.choices.split(',')
                ]
                self.fields[field_name] = forms.ChoiceField(
                    label=field.label,
                    choices=choices,
                    required=field.required,
                    widget=forms.Select(attrs={"class": field.css_class}),
                )

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        phone = re.sub(r'\D', '', phone)
        phone_len = len(phone)
        if phone_len < 10 or phone_len > 11:
            raise forms.ValidationError(_('Enter the correct phone number.'))
        return phone

    def clean(self):
        cd = super(SimpleOrderForm, self).clean()
        if cd.get('delivery_variant') and cd.get('payment_variant') not in (None, ''):
            if (
                cd['payment_variant']
                not in self.delivery_payment_mapping[cd['delivery_variant']]
            ):
                self.add_error('payment_variant', _('Incorrect payment variant'))
        return cd


def create_delivery_forms(delivery_type_class=None, *args, **kwargs):
    assert (
        delivery_type_class is None
        or delivery_type_class in models.Order.DELIVERY_MODELS
    ), 'delivery type must be a delivery model class'
    delivery_forms = {}
    active_form = None
    for delivery_class in models.Order.DELIVERY_MODELS:
        if delivery_class.__name__ not in get_config_list('DELIVERY_METHODS'):
            continue
        c_args = args[:]
        c_kwargs = kwargs.copy()
        if delivery_class != delivery_type_class:
            # if the form is of the other type copy the data from the active form to the current initial_data
            # so some fields of the form will not be empty by default
            data = c_kwargs.pop('data', None)
            if data:
                c_kwargs['initial'] = {k: v for k, v in data.items()}
            elif 'initial' in kwargs:
                c_kwargs['initial'] = kwargs['initial']
            c_kwargs.pop('instance', None)
        else:
            c_kwargs.pop('initial', None)
        form_class = globals()[delivery_class.form]
        delivery_forms[delivery_class.__name__] = form_class.create(*c_args, **c_kwargs)
        if delivery_class == delivery_type_class:
            active_form = delivery_forms[delivery_class.__name__]
    return delivery_forms, active_form


class DeliveryFormBase(forms.ModelForm):
    name = forms.CharField(
        label=_('Contact Name'), max_length=60, widget=forms.TextInput()
    )
    phone = forms.CharField(label=_('Phone'), max_length=18, widget=forms.TextInput())
    email = forms.EmailField(label=_('E-mail'), max_length=60, widget=forms.TextInput())

    class Meta:
        model = models.DeliveryBase
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.products = kwargs.pop('products', None)

        # The form can be compiled for a separate delivery calculation page.
        # Then the location will be added by its own method from the request object.
        if not hasattr(self, 'location'):
            self.location = kwargs.pop('location', None) or None

        super().__init__(*args, **kwargs)

    @classmethod
    def create(cls, *args, **kwargs):
        """
        Handy method to create a form instance by providing ANY initial data, ANY instance and ANY other kwargs.
        Use like an ordinary form constructor.
        """
        # remove fields from initial data which don't exist in the current form
        initial = kwargs.get('initial')
        if initial:
            kwargs['initial'] = {
                k: v for k, v in initial.items() if k in cls.base_fields
            }
        instance = kwargs.get('instance')
        if instance and instance.__class__ != cls.Meta.model:
            # unset the provided instance if it has a wrong delivery type
            del kwargs['instance']

        # Keep only expected kwargs.
        init_args = set(cls.__init__.__code__.co_varnames) | set(
            forms.BaseModelForm.__init__.__code__.co_varnames
        )
        # Pass some values to forms from the current request.
        init_args.update(['products', 'location'])

        safe_kwargs = {}
        for key, value in kwargs.items():
            if key in init_args:
                safe_kwargs[key] = value

        return cls(*args, **safe_kwargs)

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        phone = re.sub(r'\D', '', phone)
        return phone

    def get_content_type(self):
        return ContentType.objects.get_for_model(self.Meta.model)

    def update_field_labels(self):
        for field in self.fields:
            if self.fields[field].required:
                self.fields[field].label = mark_safe(
                    '%s<span class="required_mark required_mark__inline">*</span>'
                    % (self.fields[field].label or '')
                )


class PickUpDeliveryForm(DeliveryFormBase):
    class Meta:
        model = models.PickUpDelivery
        fields = ('name', 'phone', 'email', 'point')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['point'].widget = forms.RadioSelect()
        stock_qs = Stock.objects.filter(pickup_point=True).order_by('position')
        self.fields['point'].choices = [(point.pk, point.address) for point in stock_qs]
        self.update_field_labels()


class ToAddressDeliveryForm(DeliveryFormBase):
    class Meta:
        model = models.ToAddressDelivery
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in (
            'address_latitude',
            'address_longitude',
            'distance_km',
            'delivery_cost',
        ):
            self.fields[field].widget = forms.HiddenInput()
        self.fields['address'].widget = forms.TextInput(
            attrs={'class': 'form-control', 'autocomplete': 'new-password'}
        )
        stocks = (
            Stock.objects.all()
            if settings.DEBUG
            else Stock.objects.for_location(self.location)
        )
        self.fields['stock'].choices = [('', '---------')] + [
            (stock.pk, stock.address) for stock in stocks
        ]
        self.fields['car'].queryset = self.get_possible_cars_queryset()

    def get_possible_cars_queryset(self):
        """
        Search for a car from the available ones whose parameters are suitable
        for the delivery of products that are currently in the user's cart.
        """
        queryset = (
            models.DeliveryCar.objects.all()
            if settings.DEBUG
            else models.DeliveryCar.objects.for_location(self.location)
        )

        if self.products:
            total_volume = total_weight = 0
            for product, qty in self.products:
                if product.volume and product.volume > 0:
                    total_volume += product.volume * qty
                if product.weight and product.weight > 0:
                    total_weight += product.weight * qty

            return queryset.filter(carrying__gte=total_weight, volume__gte=total_volume)
        return queryset


class DeliveryCalculatorForm(ToAddressDeliveryForm):

    def __init__(self, *args, **kwargs):
        self.location = kwargs.pop('location')
        super().__init__(*args, **kwargs)

        del_fields = ['email', 'phone', 'name']

        if settings.DEBUG:
            # для тестов на локалке
            stock_choices = [
                (stock.pk, stock.address)
                for stock in Stock.objects.filter(pickup_point=True)
            ]
            car_choices = [
                (car.pk, car.name) for car in models.DeliveryCar.objects.all()
            ]
        else:
            stock_choices = [
                (stock.pk, stock.address)
                for stock in Stock.objects.for_location(self.location).exclude(
                    pickup_point=False
                )
            ]
            car_choices = [
                (car.pk, car.name) for car in self.get_possible_cars_queryset()
            ]

        if stock_choices:
            self.fields['stock'].choices = stock_choices
            self.fields['stock'].initial = stock_choices[0][0]
        else:
            del_fields.append('stock')

        if car_choices:
            self.fields['car'].choices = car_choices
            self.fields['car'].initial = car_choices[0][0]
        else:
            del_fields.append('car')

        for field in del_fields:
            del self.fields[field]


class ToTCDeliveryForm(DeliveryFormBase):
    class Meta:
        model = models.ToTCDelivery
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delivery_cost'].widget = forms.HiddenInput()
        self.fields['company'].widget = forms.RadioSelect()
        self.fields['company'].choices = [
            (tc.pk, tc.name) for tc in TransportCompany.objects.all()
        ]
        self.update_field_labels()


class PaymentForm(forms.Form):
    payment_method = forms.ChoiceField(widget=forms.RadioSelect())

    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop('order')
        self.base_fields['payment_method'].choices = kwargs.pop('choices')
        super().__init__(*args, **kwargs)
        if config.BILLING_INFO__VAT > 0 and hasattr(self.order.user, 'company'):
            # If the percentage of VAT is set in the settings,
            # then we display the checkbox with the question of including VAT data in the invoce.
            self.fields['invoicing_with_vat'] = forms.BooleanField(
                required=False, widget=forms.CheckboxInput(attrs={'checked': 'checked'})
            )

    def clean(self):
        cleaned_data = super().clean()
        if INVOICING is int(cleaned_data['payment_method']):
            if not self.order.user and not config.INVOICE_PDF_ANON_ALLOWED:
                self.add_error(
                    'payment_method',
                    _('Anonymous users cannot use invoicing as payment method.'),
                )
        return cleaned_data


class OrderStatusForm(forms.Form):
    order = forms.ModelChoiceField(
        queryset=Order.objects.select_related('user', 'ordercontactdata'),
        label=_('Order number'),
        widget=forms.NumberInput(
            attrs={'class': 'form-control', 'autocomplete': 'off', 'min': 1}
        ),
        error_messages={
            'invalid_choice': _(
                'The entered data was not found. Try again, there may be a mistake in the characters.'
            )
        },
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'off'})
    )

    def clean(self):
        cd = self.cleaned_data
        if cd.get('order') and cd.get('email'):
            order = cd['order']
            emails = set()
            if hasattr(order, 'ordercontactdata'):
                emails.add(order.ordercontactdata.email)
            if order.delivery:
                emails.add(order.delivery.email)
            if order.user:
                emails.add(order.user.email)
            if cd['email'].strip() not in emails:
                self.add_error('email', 'Email not found')
        return cd
