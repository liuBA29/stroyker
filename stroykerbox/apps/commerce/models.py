import decimal

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models
from django.forms.models import model_to_dict
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from constance import config
from stroykerbox.apps.utils.constance_helpers import get_config_list

from stroykerbox.apps.catalog.models import Product, Stock
from stroykerbox.apps.locations.helpers import LocationModelManager
from stroykerbox.apps.locations.models import Location
from stroykerbox.settings.constants import PAYMENT_METHODS_CHOICES
from .utils import get_payment_methods_names


class Address(models.Model):
    name = models.CharField(_('name'), max_length=256, unique=True)
    address = models.CharField(_('address'), max_length=256)
    geo_latitude = models.DecimalField(
        _('latitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_('latitude of the location'),
    )
    geo_longitude = models.DecimalField(
        _('longitude'),
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_('longitude of the location'),
    )
    location = models.ForeignKey(Location, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    @property
    def as_dict(self):
        return model_to_dict(self)


class TransportCompany(Address):
    delivery_price = models.DecimalField(
        _('delivery price'), max_digits=12, decimal_places=2
    )

    class Meta:
        verbose_name = _('transport company')
        verbose_name_plural = _('transport companies')


class DeliveryBase(models.Model):
    """
    Delivery abstract model.
    """

    name = models.CharField(_('contact person'), max_length=64)
    phone = models.CharField(
        _('phone'),
        max_length=11,
        validators=[
            validators.RegexValidator(
                r'^[78][\d]{10}$',
                _(
                    'Enter a valid phone number starting with "7 (or 8)" followed by 10 digits.'
                ),
                'invalid',
            )
        ],
    )
    email = models.EmailField(_('email'), max_length=60)
    delivery_cost = models.DecimalField(
        _('cost of delivery, rub'),
        max_digits=10,
        max_length=12,
        decimal_places=2,
        default=0,
    )

    # form class name in forms.py (can't use a class itself due to a circular import)
    form = 'DeliveryFormBase'

    # options supported: cash, online, yandex
    @classmethod
    def available_payment_methods(cls):
        raise NotImplementedError()

    @classmethod
    def get_display_name(cls):
        return cls._meta.verbose_name

    # template to render delivery details in an order notification letters
    # EMAIL_TEMPLATE = NotImplemented

    def __str__(self):
        return force_text(self.get_display_name())

    def cost(self):
        raise NotImplementedError()

    @staticmethod
    def get_cost_url():
        raise NotImplementedError()

    @property
    def as_dict(self):
        return model_to_dict(self)

    class Meta:
        abstract = True
        ordering = ('-pk',)


class PickUpDelivery(DeliveryBase):
    """
    Pickup delivery type
    """

    point = models.ForeignKey(Stock, on_delete=models.SET_NULL, null=True)

    form = 'PickUpDeliveryForm'

    @classmethod
    def available_payment_methods(cls):
        return list(
            set(get_config_list('DELIVERY_PICUP_PAYMENT_METHODS')) & set(get_config_list('PAYMENT_METHODS'))
        )

    @classmethod
    def get_display_name(cls):
        return config.DELIVERY_PICKUP_DISPLAY_NAME or super().get_display_name()

    # EMAIL_TEMPLATE = 'cart/email/pickup-delivery-details.html'

    class Meta:
        verbose_name = _('pick up delivery')
        verbose_name_plural = _('pick up deliveries')

    def cost(self):
        return config.DELIVERY_PICUP_COST

    @staticmethod
    def get_cost_url():
        pass


class ToAddressDelivery(DeliveryBase):
    """
    To Address delivery type
    """

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, null=True)
    address = models.CharField(_('address'), max_length=256)
    address_latitude = models.DecimalField(
        _('address latitude'), max_digits=13, decimal_places=9, null=True, blank=True
    )
    address_longitude = models.DecimalField(
        _('address longitude'), max_digits=13, decimal_places=9, null=True, blank=True
    )
    car = models.ForeignKey('DeliveryCar', on_delete=models.CASCADE, null=True)
    distance_km = models.PositiveIntegerField(_('distance, km'), null=True)

    form = 'ToAddressDeliveryForm'

    class Meta:
        verbose_name = _('delivery to address')
        verbose_name_plural = _('delivery to addresses')

    @classmethod
    def available_payment_methods(cls):
        return list(
            set(get_config_list('DELIVERY_TOADDRESS_PAYMENT_METHODS')) & set(get_config_list('PAYMENT_METHODS'))
        )

    @classmethod
    def get_display_name(cls):
        return config.DELIVERY_TOADDRESS_DISPLAY_NAME or super().get_display_name()

    def cost(self):
        cost = self.delivery_cost
        if config.DELIVERY_TOADDRESS_COST > 0:
            cost += config.DELIVERY_TOADDRESS_COST
        return cost

    @staticmethod
    def get_cost_url():
        return reverse('cart:ajax_get_delivery_to_address_cost')


class ToTCDelivery(DeliveryBase):
    """
    To Transport Company delivery type
    """

    company = models.ForeignKey(TransportCompany, on_delete=models.CASCADE)

    form = 'ToTCDeliveryForm'

    class Meta:
        verbose_name = _('delivery to tc')
        verbose_name_plural = _('delivery to tc')

    @classmethod
    def available_payment_methods(cls):
        return list(
            set(get_config_list('DELIVERY_TOTC_PAYMENT_METHODS')) & set(get_config_list('PAYMENT_METHODS'))
        )

    @classmethod
    def get_display_name(cls):
        return config.DELIVERY_TOTC_DISPLAY_NAME or super().get_display_name()

    def cost(self):
        cost = 0
        if self.company:
            cost = self.company.delivery_price
        if config.DELIVERY_TOTC_COST > 0:
            cost += config.DELIVERY_TOTC_COST
        return cost

    @staticmethod
    def get_cost_url():
        return reverse('cart:ajax_get_delivery_to_tc_cost')


class OrderManager(models.Manager):
    def get_visible_for_user(self):
        return self.filter(status__in=Order.STATUSES_VISIBLE_FOR_USER)


class Order(models.Model):
    """
    Order
    """

    DELIVERY_MODELS = (PickUpDelivery, ToAddressDelivery, ToTCDelivery)

    STATUS_CHOICES = (
        ('draft', _('Draft order')),
        ('new', _('New order')),
        ('processed', _('Processed')),
        ('in_progress', _('In progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    )

    YOOKASSA_PENDING = 'pending'
    YOOKASSA_SUCCEEDED = 'succeeded'
    WAITING_FOR_CAPTURE = 'waiting_for_capture'
    YOOKASSA_CANCELED = 'canceled'

    YOOKASSA_PAYMENT_STATUS_CHOICES = (
        (YOOKASSA_PENDING, _('Pending')),
        (WAITING_FOR_CAPTURE, _('Waiting for capture')),
        (YOOKASSA_SUCCEEDED, _('Succeeded')),
        (YOOKASSA_CANCELED, _('Canceled')),
    )

    # All possible status choices for the current order state.
    POSSIBLE_STATUS_CHOICES = {'new', 'cancelled'}

    # Orders to show to a user at the profile page.
    STATUSES_VISIBLE_FOR_USER = ('new', 'processed', 'in_progress', 'completed')

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        default=None,
        related_name='orders',
    )
    delivery_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': [c.__name__.lower() for c in DELIVERY_MODELS]},
        null=True,
    )
    delivery_id = models.PositiveIntegerField(null=True)
    delivery = GenericForeignKey('delivery_type', 'delivery_id')
    total_price = models.DecimalField(
        _('sum of all the products prices'),
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        default=None,
        help_text=_('Sum of all the products personal prices and their quantities.'),
    )
    final_price = models.DecimalField(
        _('final price of the order'),
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        default=None,
        help_text=_(
            'Final price of the order to be paid by a customer including a delivery cost.'
        ),
    )
    is_paid = models.BooleanField(
        _('order is paid'),
        default=False,
        db_index=True,
        help_text=_('Flag of the payment status of the order.'),
    )
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text=_('Global order status.'),
    )
    status_changed_at = models.DateTimeField(
        _('status changed at'), db_index=True, null=True
    )
    products = models.ManyToManyField(Product, through='OrderProductMembership')
    comment = models.TextField(
        _('comment'), default='', blank=True, help_text=_('Comment on the order.')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, db_index=True)
    payment_method = models.PositiveSmallIntegerField(
        _('payment method'), choices=get_payment_methods_names(as_dict=False), null=True
    )
    yookassa_status = models.CharField(
        _('yookassa payment status'), max_length=19, blank=True, null=True
    )
    invoicing_with_vat = models.BooleanField(_('invoicing with VAT'), default=True)
    from_cart = models.BooleanField(
        _('created from cart'),
        help_text=_('Created from the cart content, not manually by a manager.'),
        default=False,
    )
    location = models.ForeignKey(Location, null=True, on_delete=models.SET_NULL)
    shipped = models.BooleanField(
        _('order is shipped'),
        default=False,
        help_text=_('Flag of the shipping status of the order to the customer.'),
    )
    closing_document = models.FileField(
        _('Closing document'), blank=True, null=True, upload_to='order/documents'
    )
    delivery_cart_simple_mode = models.TextField(
        _('Delivery if simple mode'), blank=True, null=True
    )

    objects = OrderManager()

    def __init__(self, *args, **kwargs):
        super(Order, self).__init__(*args, **kwargs)
        self._original_status = self.status
        self._swap_class()

    @property
    def order_user_name(self):
        if hasattr(self, 'ordercontactdata'):
            return self.ordercontactdata.name
        elif self.user:
            return self.user.name or self.user.company or self.user.email
        return getattr(self.delivery, 'name', None)

    @property
    def order_user_email(self):
        if self.user:
            return self.user.email
        elif hasattr(self, 'ordercontactdata'):
            return self.ordercontactdata.email
        return getattr(self.delivery, 'email', None)

    @property
    def order_user_phone(self):
        if self.user:
            return self.user.phone
        elif hasattr(self, 'ordercontactdata'):
            return self.ordercontactdata.phone
        return getattr(self.delivery, 'phone', None)

    def save(self, *args, **kwargs):
        if not kwargs.pop('skip_validation', False):
            self.clean()
        if self._original_status != self.status:
            self._original_status = self.status
            self.status_changed_at = now()
            self._swap_class()
            # Call apply_transition() on a new class.
            self.apply_transition()
        return super(Order, self).save(*args, **kwargs)

    def clean(self):
        # Check if the status has been changed, if so, validate the new status.
        if (
            self._original_status != self.status
            and self.status not in self.POSSIBLE_STATUS_CHOICES
        ):
            raise ValidationError(
                '{class_name} can not be set to the status "{status}"'.format(
                    class_name=self.__class__.__name__, status=self.status
                )
            )

    def __str__(self):
        return (
            _('Order from ')
            + f'{self.created_at.strftime("%Y-%m-%d %H:%M")} #{self.pk}'
        )

    def _swap_class(self):
        self.__class__ = STATUS_TO_CLASS_MAPPER[self.status]

    class Meta:
        ordering = ('-created_at',)
        verbose_name = _('order')
        verbose_name_plural = _('orders')

    def apply_transition(self):
        """This method is called whenever the new status is saved in the save() method.

        All transition logic must be implemented here.
        """
        pass

    def get_absolute_url(self):
        return reverse('users:order_details', kwargs={'order_pk': self.pk})

    @property
    def include_vat(self):
        """
        A flag indicating whether to include VAT in the invoice.
        If the invoice payment method is selected.
        """
        return (config.BILLING_INFO__VAT > 0) and self.invoicing_with_vat

    @property
    def total_quantity(self):
        return sum(
            q
            for q in OrderProductMembership.objects.values_list(
                'quantity', flat=True
            ).filter(order=self)
        )

    @property
    def total_weight(self):
        return sum(
            q
            for q in OrderProductMembership.objects.values_list(
                'weight', flat=True
            ).filter(order=self, weight__gt=0)
        )

    @cached_property
    def delivery_cost(self):
        if self.delivery:
            return self.delivery.delivery_cost

    @cached_property
    def total_price_vat(self):
        if config.BILLING_INFO__VAT:
            coeff = decimal.Decimal(config.BILLING_INFO__VAT / 100)
            return round((self.total_price * coeff) / (1 + coeff), 2)
        return 0

    @property
    def as_dict(self):
        result = model_to_dict(self)
        result['delivery'] = str(self.delivery)
        result['products'] = [
            p.as_dict for p in OrderProductMembership.objects.filter(order=self)
        ]
        result['total_quantity'] = self.total_quantity
        result['total_weight'] = self.total_weight
        result['created_at'] = str(self.created_at)
        result['user'] = self.user if self.user else _('Anonymous')
        result['delivery_cost'] = self.delivery_cost
        result['include_vat'] = self.include_vat
        if self.include_vat:
            result['total_price_vat'] = self.total_price_vat
        result['payment_method'] = self.payment_method_name
        return result

    @property
    def status_name(self):
        return dict(self.STATUS_CHOICES)[self.status]

    @property
    def payment_method_name(self):
        if self.payment_method is not None:
            names_dict = get_payment_methods_names()
            return names_dict.get(
                self.payment_method,
                dict(PAYMENT_METHODS_CHOICES).get(self.payment_method),
            )

    def populate_from_cart(self, cart):
        """
        Populate order instance with data from cart. Order instance must be saved before using this method.
        """
        if cart.user.is_authenticated:
            self.user = cart.user
        else:
            self.user = None
        self.total_price = cart.total_price
        self.final_price = cart.final_price
        cart_products_pks = set(cart.products.keys())
        order_products_pks = {p.pk for p in self.products.all()}
        missed_products_pks = cart_products_pks - order_products_pks
        deleted_products_pks = order_products_pks - cart_products_pks
        # remove products from order which were deleted in cart
        OrderProductMembership.objects.filter(
            order=self, product__pk__in=deleted_products_pks
        ).delete()
        # add missed products to this order
        for mp_pk in missed_products_pks:
            product = Product.objects.get(pk=mp_pk)
            quantity = cart.products[mp_pk]
            weight = quantity * product.weight if product.weight > 0 else 0
            OrderProductMembership.objects.create(
                order=self,
                product=product,
                product_price=product.price,
                personal_product_price=cart.product_cart_price(product),
                quantity=quantity,
                weight=weight,
            )


class OrderContactData(models.Model):
    """
    Helper class that stores customer data when the cart is running in simplified mode.
    """

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    name = models.CharField(_('name'), max_length=64)
    phone = models.CharField(_('phone'), max_length=11)
    email = models.EmailField(_('email'), max_length=60)


class OrderNew(Order):
    POSSIBLE_STATUS_CHOICES = {'processed', 'completed', 'cancelled'}

    class Meta:
        proxy = True

    def apply_transition(self):
        """
        Withhold the bonuses from user, set the promo code as used.
        """
        pass


class OrderProcessed(Order):
    POSSIBLE_STATUS_CHOICES = {'in_progress', 'completed', 'cancelled'}

    class Meta:
        proxy = True

    def apply_transition(self):
        pass


class OrderInProgress(Order):
    POSSIBLE_STATUS_CHOICES = {'completed', 'cancelled'}

    class Meta:
        proxy = True

    def apply_transition(self):
        pass


class OrderCompleted(Order):
    POSSIBLE_STATUS_CHOICES = {'cancelled'}

    class Meta:
        proxy = True

    def apply_transition(self):
        """
        Mark the order as completed, give to the user his earned bonuses.
        """
        pass


class OrderCancelled(Order):
    POSSIBLE_STATUS_CHOICES = set()

    class Meta:
        proxy = True

    def apply_transition(self):
        """Mark the order as cancelled: return all the bonuses to user."""
        pass


STATUS_TO_CLASS_MAPPER = {
    'draft': Order,
    'new': OrderNew,
    'processed': OrderProcessed,
    'in_progress': OrderInProgress,
    'completed': OrderCompleted,
    'cancelled': OrderCancelled,
}


class OrderProductMembership(models.Model):
    """
    Product in order membership
    """

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='order_products'
    )
    product_price = models.DecimalField(
        _('product price'),
        help_text=_('Product price at the moment of purchase'),
        max_digits=12,
        decimal_places=0,
    )
    personal_product_price = models.DecimalField(
        _('personal product price'),
        help_text=_('Personal product price at the moment of purchase'),
        max_digits=12,
        decimal_places=2,
    )
    quantity = models.PositiveSmallIntegerField(_('product quantity sum'))
    weight = models.FloatField(_('product weight sum, kg'), default=0)

    @property
    def as_dict(self):
        result = model_to_dict(self)
        result['product'] = self.product.as_dict
        return result


class DeliveryCar(models.Model):
    location = models.ForeignKey(Location, null=True, on_delete=models.CASCADE)
    name = models.CharField(_('car model'), max_length=255)
    carrying = models.PositiveSmallIntegerField(_('carrying, kg'))
    volume = models.FloatField(_('volume, m3'))
    length = models.FloatField(_('length, m'), default=0)
    height = models.FloatField(_('height, m'), default=0)
    width = models.FloatField(_('width, m'), default=0)
    store_start_cost = models.DecimalField(
        _('cost of start from store, rub'),
        max_digits=10,
        max_length=12,
        decimal_places=2,
        default=0,
    )
    cost_km = models.DecimalField(
        _('cost of km, rub'), max_digits=10, max_length=12, decimal_places=2, default=0
    )
    position = models.PositiveIntegerField(_('position'), default=0)
    objects = LocationModelManager()

    class Meta:
        ordering = ('position', 'carrying')
        verbose_name = _('delivery car')
        verbose_name_plural = _('delivery cars')

    def __str__(self):
        return self.name


class YookassaData(models.Model):
    """Информация что было передано и получено через yookassa"""

    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    slug = models.CharField(_('slug for confirm payment'), max_length=32, unique=True)
    yookassa_id = models.CharField(
        _('ID payment into yookassa'), max_length=36, blank=True, default=''
    )
    request_create = models.JSONField(_('Данные, которые отправили в юкассу'))
    response_create = models.JSONField(
        _('Данные, которые получили после создания платежа')
    )
    log = models.JSONField('логи проверки статуса', default=dict, blank=True)

    status = models.CharField(
        _('yookassa payment status'),
        max_length=19,
        choices=Order.YOOKASSA_PAYMENT_STATUS_CHOICES,
    )

    created = models.DateTimeField(_('date created'), auto_now_add=True)

    class Meta:
        ordering = ('-created',)
        verbose_name = _('Yoomoney payment')
        verbose_name_plural = _('Yoomoney payments')

    def __str__(self):
        return f'{self.order}:{self.created}'

    def write_to_log(self, data, save=True):
        if not isinstance(self.log, dict):
            self.log = {}
        self.log.update({f'{timezone.now()}': data})
        if save:
            self.save(update_fields=('log',))


(
    BINDED_ALL,
    BINDED_PICKUP_DELIVERY,
    BINDED_ADDRESS_DELIVERY,
    BINDED_TK_DELIVERY,
    BINDED_PAYMENT_0,
    BINDED_PAYMENT_1,
    BINDED_PAYMENT_2,
    BINDED_PAYMENT_3,
    BINDED_PAYMENT_4,
    BINDED_PAYMENT_5,
) = range(1, 11)

FIELD_BINDINGS = (
    (BINDED_ALL, 'Всегда'),
    (BINDED_PICKUP_DELIVERY, 'При самовывозе'),
    (BINDED_ADDRESS_DELIVERY, 'При доставке по адресу'),
    (BINDED_TK_DELIVERY, 'При доставке до ТК'),
    (BINDED_PAYMENT_0, 'При оплате через счет'),
    (BINDED_PAYMENT_1, 'При оплате картой при получении'),
    (BINDED_PAYMENT_2, 'При оплате наличными при получении'),
    (BINDED_PAYMENT_3, 'При оплате онлайн'),
    (BINDED_PAYMENT_4, 'При оплате в кредит'),
    (BINDED_PAYMENT_5, 'При оплате через Yookassa'),
)


class OrderExtraField(models.Model):
    """
    Дополнительные поля в заказе
    """

    FIELD_TYPES = (
        ('text', _('Текстовое поле')),
        ('textarea', _('Текстовая область')),
        ('select', _('Выпадающий список')),
        ('label', _('Метка (Label)')),
    )
    DELIVERY_MODELS = (PickUpDelivery, ToAddressDelivery, ToTCDelivery)

    name = models.CharField(_('Название поля'), max_length=100)
    label = models.CharField(_('метка перед полем'), max_length=200, blank=True)
    comment = models.CharField(_('метка внутри поля'), max_length=200, blank=True)
    field_type = models.CharField(_('Тип поля'), max_length=20, choices=FIELD_TYPES)
    required = models.BooleanField(
        _('Обязательное поле'),
        default=False,
        help_text='работает только в полной корзине',
    )
    choices = models.TextField(_('Значения списка (для select)'), blank=True)
    position = models.PositiveIntegerField(_('Позиция вывода'), default=0)
    css_class = models.CharField(
        _('Дополнительный CSS класс'), max_length=100, blank=True
    )
    binded_to = models.IntegerField(
        _('Привязка поля'),
        choices=FIELD_BINDINGS,
        default=1,
    )
    amocrm_field_id = models.PositiveIntegerField(
        'AMOcrm ID', help_text='Привязка поля к полю в AMOcrm.', null=True, blank=True
    )

    class Meta:
        ordering = ['position']
        verbose_name = _('Дополнительное поле')
        verbose_name_plural = _('Дополнительные поля')

    def __str__(self):
        return self.name

    def clean(self):
        if self.required and self.binded_to is not BINDED_ALL:
            raise ValidationError(
                {'required': 'Обязательность доступна только для общих полей.'}
            )


class OrderExtraFieldValue(models.Model):
    """
    Значения дополнительных полей в заказе
    """

    order = models.ForeignKey(
        'Order',
        verbose_name=_('Заказ'),
        on_delete=models.CASCADE,
        related_name='extra_field_values',
    )
    field = models.ForeignKey(
        'OrderExtraField',
        verbose_name=_('Дополнительное поле'),
        on_delete=models.CASCADE,
    )
    value = models.TextField(_('Значение'))

    class Meta:
        verbose_name = _('Значение дополнительного поля')
        verbose_name_plural = _('Значения дополнительных полей')

    def __str__(self):
        return f'{self.field.name}: {self.value}'
