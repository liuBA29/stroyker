from typing import Any

from django.db import models
from django.utils.translation import ugettext as _
from django.contrib.auth import get_user_model
from django.db.models.base import ModelBase
from django.contrib.sites.models import Site
from django.urls import reverse
from django.template.loader import render_to_string
from constance import config

from stroykerbox.apps.locations.models import Location
from stroykerbox.settings.constants import YOOKASSA

from .utils import get_order_model


User = get_user_model()
Order = get_order_model()

(
    CRM_REQUEST_NEW,
    CRM_REQUEST_CREATED,
    CRM_REQUEST_CANCEL,
    CRM_REQUEST_CALL_LATER,
    CRM_REQUEST_COMPLETE,
) = range(5)
CRM_REQUEST_STATUSES = (
    (CRM_REQUEST_NEW, _('new')),
    (CRM_REQUEST_CREATED, _('order created')),
    (CRM_REQUEST_CANCEL, _('canceled')),
    (CRM_REQUEST_CALL_LATER, _('call back later')),
    (CRM_REQUEST_COMPLETE, _('completed')),
)


class CrmRequestBaseMeta(ModelBase):
    """
    Metaclass for CrmRequestBase.
    An object of this type will always be an instance of its own class,
    even if called as an object of a base class.
    """

    def __call__(cls, *args, **kwargs):
        obj = super().__call__(*args, **kwargs)
        return obj.get_object()


class CrmRequestBase(models.Model, metaclass=CrmRequestBaseMeta):
    """
    Base CRM Request model. Used as a parent class for all concrete crm requests
    and comprises all common fields.
    """

    order = models.OneToOneField(
        Order, null=True, blank=True, on_delete=models.SET_NULL
    )
    name = models.CharField(_('customer name'), max_length=255)
    phone = models.CharField(_('customer phone'), max_length=50)
    message = models.TextField(_('customer message text'), null=True, blank=True)
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('manager'),
    )
    manager_comment = models.TextField(_('manager_comment'), null=True, blank=True)
    created = models.DateTimeField(_('request date'), auto_now_add=True)
    changed = models.DateTimeField(_('changed'), auto_now=True)
    status = models.PositiveSmallIntegerField(
        _('status'),
        choices=CRM_REQUEST_STATUSES,
        default=CRM_REQUEST_NEW,
        db_index=True,
    )
    location = models.ForeignKey(
        Location, null=True, blank=True, on_delete=models.SET_NULL
    )

    # https://redmine.fancymedia.ru/issues/12839
    utm_campaign = models.CharField(
        'метка utm_campaign', max_length=128, null=True, blank=True
    )
    utm_content = models.CharField(
        'метка utm_content', max_length=128, null=True, blank=True
    )
    utm_medium = models.CharField(
        'метка utm_medium', max_length=128, null=True, blank=True
    )
    utm_source = models.CharField(
        'метка utm_source', max_length=128, null=True, blank=True
    )
    utm_term = models.CharField('метка utm_term', max_length=128, null=True, blank=True)
    page_url = models.CharField(
        'страница отправки формы', max_length=255, null=True, blank=True
    )

    object_class = models.CharField(max_length=40)

    class Meta:
        ordering = ('-created',)
        verbose_name = _('crm request')
        verbose_name_plural = _('crm requests')

    def __str__(self):
        return _('CRM Request through the') + ' {} Model'.format(self.object_class)

    def save(self, *args, **kwargs):
        if not self.object_class:
            self.object_class = self._meta.model_name
        super().save(*args, **kwargs)

    def get_object(self):
        if not self.object_class or self._meta.model_name == self.object_class:
            return self
        return getattr(self, self.object_class)

    @property
    def b24_utm(self):
        from .forms import HIDDEN_EXT_FIELDS

        # https://redmine.fancymedia.ru/issues/12839
        output = {}
        for key, fieldname in HIDDEN_EXT_FIELDS.items():
            if key == 'PAGE_URL_FIELDNAME':
                continue
            output[fieldname.upper()] = getattr(self, fieldname, '')
        return output

    @property
    def b24_title(self):
        return _('Request ID %(id)s from site %(site)s') % {
            'id': self.pk,
            'site': Site.objects.get_current().domain,
        }

    def get_b24_phone(self, phone):
        return [{'VALUE': phone, 'VALUE_TYPE': 'WORK'}]

    def get_b24_email(self, email):
        return [{'VALUE': email, 'VALUE_TYPE': 'WORK'}]

    def get_b24_yookassa_amount(self):
        amount = self.order.final_price
        try:
            match config.B24_YOOKASSA_FIELD_TYPE:
                case 'str':
                    amount = str(amount)
                case 'int':
                    amount = int(amount)
                case 'float':
                    amount = float(amount)
        except ValueError:
            # по-дефолту цену отправляем в том типe, в котором она содержиться в заказе.
            pass
        return amount

    def get_b24_yookassa_payment_data(self) -> dict[str, Any] | None:
        """
        https://redmine.fancymedia.ru/issues/13218
        """
        if not config.B24_YOOKASSA_FIELD_NAME or (
            self.order
            and (self.order.payment_method == YOOKASSA and self.order.is_paid)
        ):
            return None

        if amount := self.get_b24_yookassa_amount():
            return {config.B24_YOOKASSA_FIELD_NAME: amount}

    @property
    def b24_fields(self):
        fields_dict = {
            'TITLE': self.b24_title,
            'NAME': self.name,
            'COMMENTS': self.message,
            'SOURCE_DESCRIPTION': self._meta.verbose_name.capitalize(),
            'SOURCE_ID': 'WEBFORM',  # "Реклама в интернете"
        }
        if yookassa_field_dict := self.get_b24_yookassa_payment_data():
            fields_dict.update(yookassa_field_dict)

        if self.phone:
            fields_dict['PHONE'] = self.get_b24_phone(self.phone)
        if self.order:
            if self.order.final_price:
                fields_dict['OPPORTUNITY'] = float(self.order.final_price)
            admin_url = reverse('admin:commerce_order_change', args=[self.order.pk])
            fields_dict['COMMENTS'] = (
                f'{getattr(self.order, "comment", "")}\n '
                f'http://{Site.objects.get_current().domain}{admin_url}'
            )
            comments = []
            if self.order.comment:
                comments.append(self.order.comment)
            if self.message:
                comments.append(self.message)
            fields_dict['COMMENTS'] = '\n'.join(comments)

            if self.order.user:
                user_email = self.order.user.email
            elif hasattr(self.order, 'ordercontactdata'):
                user_email = self.order.ordercontactdata.email
            else:
                user_email = getattr(self.order.delivery, 'email', None)
            if user_email:
                fields_dict['EMAIL'] = self.get_b24_email(user_email)

        # https://redmine.fancymedia.ru/issues/12839
        if self.page_url:
            fields_dict['WEB'] = self.page_url
        fields_dict.update(self.b24_utm)

        return {k: v for k, v in fields_dict.items() if v}


class CallMeRequest(CrmRequestBase):
    """
    The request is created when a customer submits a call-me request form.
    """

    class Meta:
        ordering = ('-created',)
        verbose_name = _('call-me request')
        verbose_name_plural = _('call-me requests')

    def __str__(self):
        return _('Call-Me Request from') + ' {} {}'.format(self.name, self.phone)

    @property
    def b24_title(self):
        return f'Запрос обратного звонка с сайта {Site.objects.get_current().domain}'


class FeedbackMessageRequest(CrmRequestBase):
    """
    The request is created when the client submits a form with a some message.
    """

    email = models.EmailField(_('customer email'), null=True)

    def __str__(self):
        return _('Feedback Message from') + ' {} {}'.format(self.name, self.email)

    class Meta:
        ordering = ('-created',)
        verbose_name = _('customer message')
        verbose_name_plural = _('customer messages')

    @property
    def b24_title(self):
        return f'Запрос через форму обратной связи с сайта {Site.objects.get_current().domain}'

    @property
    def b24_fields(self):
        fields_dict = super().b24_fields
        if self.email:
            fields_dict['EMAIL'] = self.get_b24_email(self.email)
        return fields_dict


class FromCartRequest(CrmRequestBase):
    """
    A request created when the user creates an order through the cart.
    """

    class Meta:
        ordering = ('-created',)
        verbose_name = _('request from cart')
        verbose_name_plural = _('requests from cart')

    @property
    def b24_title(self):
        return f'Новый заказ на сайте {Site.objects.get_current().domain}'

    @property
    def b24_fields(self):
        fields_dict = super().b24_fields

        if 'COMMENTS' not in fields_dict:
            fields_dict['COMMENTS'] = ''
        fields_dict['COMMENTS'] += render_to_string(
            'crm/b24-order-products.html', {'order': self.order}
        )
        return fields_dict


class GiftForPhoneRequest(CrmRequestBase):
    """
    The request is created when a customer submits phone number for a some gift (link to download).
    """

    class Meta:
        ordering = ('-created',)
        verbose_name = _('gift for phone request')
        verbose_name_plural = _('gift for phone requests')

    def __str__(self):
        return _('Gift for phone request: ') + ' (tel. {})'.format(self.phone)

    @property
    def b24_title(self):
        return _('Запрос подарка за телефон с сайта %(domain)s') % {
            'domain': Site.objects.get_current().domain
        }
