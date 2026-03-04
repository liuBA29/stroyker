from typing import Optional
import logging

from django.utils.text import Truncator
from django.db.models import Sum
from django.conf import settings
from constance import config
import requests

from stroykerbox.apps.utils.utils import string_to_int

logger = logging.getLogger(__name__)


def amocrm_is_enabled():
    return settings.DEBUG or all(
        (
            config.AMOCRM_ENABLED,
            config.AMOCRM_BASE_URL,
            config.AMOCRM_LONG_ACCESS_TOKEN,
            config.AMOCRM_DEFAULT_METHOD,
        )
    )


class AMOCrmDisabledException(Exception):
    pass


class Amo:

    def __init__(self, crm_object, **kwargs):
        if not amocrm_is_enabled() and not settings.DEBUG:
            raise AMOCrmDisabledException
        method = kwargs.get('method', config.AMOCRM_DEFAULT_METHOD)
        amo_base_url = config.AMOCRM_BASE_URL.rstrip('/')

        self.amo_api_url = f'{amo_base_url}{method}'
        self.crm_object = crm_object
        self.crm_object_order = getattr(self.crm_object, 'order', None)
        self.crm_model_name = self.crm_object.__class__.__name__.lower()

    def _get_token(self):
        return getattr(config, 'AMOCRM_LONG_ACCESS_TOKEN', '')

    def _get_headers(self):
        token = self._get_token()
        return {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}

    def get_order_extra_field_as_message(self) -> Optional[str]:
        """
        https://redmine.nastroyker.ru/issues/14501
        """
        if not self.crm_object_order or not hasattr(
            self.crm_object_order, 'extra_field_values'
        ):
            return None

        output = self.crm_object_order.extra_field_values.filter(
            field__amocrm_field_id__isnull=True
        ).values_list('value', flat=True)

        return '\n'.join(output)

    def get_order_extra_field_values(self) -> Optional[list]:
        """
        https://redmine.nastroyker.ru/issues/14501
        """
        if not self.crm_object_order or not hasattr(
            self.crm_object_order, 'extra_field_values'
        ):
            return None

        output = []
        for item in self.crm_object_order.extra_field_values.filter(
            field__amocrm_field_id__isnull=False
        ):
            output.append(
                {
                    'field_id': item.field.amocrm_field_id,
                    'values': [
                        {
                            'value': item.value,
                        }
                    ],
                }
            )
        return output

    def get_customer_message(self, chars_limit=256) -> Optional[str]:
        """
        Получение значения для поля "сообщение(комментарий)" из crm-объекта.
        """
        if not config.AMOCRM_CONTACT_MSG_FIELD_ID:
            return None

        message = ''

        if self.crm_object_order:
            message = self.crm_object_order.comment
        else:
            message = getattr(self.crm_object, 'message', '')
        if extra_field_message := self.get_order_extra_field_as_message():
            # https://redmine.nastroyker.ru/issues/14501
            if message:
                message += f'\n{extra_field_message}'
            else:
                message = extra_field_message
        if message:
            return Truncator(message).chars(chars_limit)

    def get_order_data(self):
        """
        Только для crm-объектов заказов через корзину (FromCartRequest).
        Получение списка (строкой) товаров из заказа.
        """
        if (
            not config.AMOCRM_CONTACT_ORDER_DATA_FIELD_ID
            or not self.crm_object_order
            or not self.crm_object_order.products.exists()
        ):
            return

        order_products = self.crm_object_order.order_products.all()

        output = []
        output.append(
            f'Количество отдельных товаров в заказе: {order_products.count()}'
        )

        total_products_qty = order_products.aggregate(qty_total=Sum('quantity'))[
            'qty_total'
        ]
        output.append(f'Общее количество заказанных товаров: {total_products_qty}')

        output += [f'{p.product.name} ({p.quantity})' for p in order_products]
        if config.AMOCRM_CONTACT_ORDER_DATA_FIELDTYPE == 'text':
            delimiter = config.AMOCRM_DATA_DELIMITER
        else:
            delimiter = '\n'
        return f'{delimiter}'.join(output)

    def get_email(self):
        """
        Получение email-адреса покупателя из crm-объекта.
        """
        if self.crm_object_order:
            return self.crm_object_order.order_user_email
        return getattr(self.crm_object, 'email', None)

    def get_phone(self):
        """
        Получение телефона покупателя из crm-объекта.

        https://redmine.fancymedia.ru/issues/12989
        На стороне AMO поле phone настроено, как числовое(касательно кейса в задаче).
        Если потом решат поменять на строчное, то опять пойдут ошибки.
        """
        if self.crm_object_order:
            phone = self.crm_object_order.order_user_phone
        else:
            phone = getattr(self.crm_object, 'phone', None)
        if config.AMOCRM_CONTACT_PHONE_FIELDTYPE == 'int':
            return string_to_int(phone)
        return phone

    def get_price(self):
        """
        Только для crm-объектов заказов через корзину (FromCartRequest).
        Получение конечной стоимости товаров заказа.
        """
        if self.crm_object_order:
            return int(self.crm_object_order.final_price)

    def get_customer_name(self):
        """
        Получение "имени" покупателя из crm-объекта.
        """
        return getattr(self.crm_object, 'name', None)

    def get_lead_name(self):
        """
        Вычисление "заголовка-имени" для лида в AMO.
        """
        if self.crm_model_name == 'callmerequest':
            return f'Запросы обратного звонка с сайта {config.SITE_NAME}'
        if self.crm_model_name == 'feedbackmessagerequest':
            return f'Сообщения через форму с сайта {config.SITE_NAME}'
        if self.crm_model_name == 'fromcartrequest':
            return f'Заказ через корзину с сайта {config.SITE_NAME}'
        if self.crm_model_name == 'giftforphonerequest':
            return f'Запрос подарка за телефон с сайта {config.SITE_NAME}'
        if self.crm_model_name == 'customformresult':
            return f'Сообщение через форму "{self.crm_object.form.title}" с сайта {config.SITE_NAME}'

    def get_contacts(self):
        """
        Получение списка словарей с контактными данными на основе кастомных полей,
        заданных в AMO (id-шники должны быть указаны в настройках).

        Не для "кастомных форм".
        """
        if self.crm_model_name == 'customformresult':
            return

        custom_fields_values = []

        if config.AMOCRM_CONTACT_NAME_FIELD_ID:
            name = self.get_customer_name()
            if name:
                custom_fields_values.append(
                    {
                        'field_id': config.AMOCRM_CONTACT_NAME_FIELD_ID,
                        'values': [{'value': name}],
                    }
                )

        if config.AMOCRM_CONTACT_EMAIL_FIELD_ID:
            email = self.get_email()
            if email:
                custom_fields_values.append(
                    {
                        'field_id': config.AMOCRM_CONTACT_EMAIL_FIELD_ID,
                        'values': [{'value': email}],
                    }
                )
        if config.AMOCRM_CONTACT_PHONE_FIELD_ID:
            phone = self.get_phone()
            if phone:
                custom_fields_values.append(
                    {
                        'field_id': config.AMOCRM_CONTACT_PHONE_FIELD_ID,
                        'values': [{'value': phone}],
                    }
                )

        return custom_fields_values

    def get_custom_forms_fields_list(self):
        """
        Получение значений "кастомных форм".
        Сопоставления полей с id-шниками AMO осуществляется через модель
        custom_forms.CustomFormFieldAMO.
        """
        if self.crm_model_name != 'customformresult':
            return
        output = []
        form_fields = self.crm_object.form.fields.filter(amocrm__isnull=False)
        for field in form_fields:
            value = self.crm_object.results.get(field.html_name)

            # https://redmine.fancymedia.ru/issues/12989
            # На стороне AMO поле phone настроено, как числовое(касательно кейса в задаче).
            if (
                field.field_class.lower().endswith('phonefield')
                and config.AMOCRM_CONTACT_PHONE_FIELDTYPE == 'int'
            ):
                value = string_to_int(value)
            output.append(
                {
                    'field_id': field.amocrm.amo_id,
                    'values': [
                        {
                            'value': value,
                        }
                    ],
                }
            )
        return output

    def get_request_fields_dict(self):
        """
        Получение данных для отправки в AMOCRM.
        """
        output = {'name': self.get_lead_name()}
        if config.AMOCRM_FIELD_STATUS_ID:
            output['status_id'] = config.AMOCRM_FIELD_STATUS_ID
            if config.AMOCRM_FIELD_PIPELINE_ID:
                output['pipeline_id'] = config.AMOCRM_FIELD_PIPELINE_ID
        price = self.get_price()
        if price:
            output['price'] = price

        custom_fields_values = []

        contacts = self.get_contacts()
        if contacts:
            custom_fields_values += contacts

        if config.AMOCRM_CONTACT_MSG_FIELD_ID:
            if message := self.get_customer_message():
                custom_fields_values.append(
                    {
                        'field_id': config.AMOCRM_CONTACT_MSG_FIELD_ID,
                        'values': [{'value': message}],
                    }
                )

        if config.AMOCRM_CONTACT_ORDER_DATA_FIELD_ID:
            order_data = self.get_order_data()
            if order_data:
                custom_fields_values.append(
                    {
                        'field_id': config.AMOCRM_CONTACT_ORDER_DATA_FIELD_ID,
                        'values': [{'value': order_data}],
                    }
                )

        if config.AMOCRM_DELIVERY_METHOD_FIELD_ID:
            if delivery_method := self.get_order_delivery_method():
                custom_fields_values.append(
                    {
                        'field_id': config.AMOCRM_DELIVERY_METHOD_FIELD_ID,
                        'values': [{'value': delivery_method}],
                    }
                )

        if config.AMOCRM_PAYMENT_METHOD_FIELD_ID:
            if payment_method := self.get_order_payment_method():
                custom_fields_values.append(
                    {
                        'field_id': config.AMOCRM_PAYMENT_METHOD_FIELD_ID,
                        'values': [{'value': payment_method}],
                    }
                )

        if custom_form_fields := self.get_custom_forms_fields_list():
            custom_fields_values += custom_form_fields

        if order_extra := self.get_order_extra_field_values():
            custom_fields_values += order_extra

        if custom_fields_values:
            output['custom_fields_values'] = custom_fields_values

        return output

    def add_lead(self):
        """
        Сбор данных и отправка их в AMOCRM (с созданием нового лида (сделки)).
        """
        try:
            json_data_dict = self.get_request_fields_dict()

            # для тестов на локалке
            if settings.DEBUG:
                return json_data_dict

            headers = self._get_headers()

            resp = requests.post(
                self.amo_api_url, json=[json_data_dict], headers=headers
            )
            r_json = resp.json()
            if resp.status_code == 200:
                logger.info(
                    f'Данные по новому crm-объекту {self.crm_object} успешно '
                    f'отправлены на сервер AMOCRM.\nResponse data: {r_json}'
                )
                return 'SUCCESS'
            else:
                logger.error(
                    f'Fail for {self.crm_object}:\n{json_data_dict=}\n{r_json=}'
                )
        except Exception as e:
            logger.exception(e)

    def get_order_delivery_method(self) -> Optional[str]:
        """
        Для заказов через корзину. Получение метода доставки.
        https://redmine.nastroyker.ru/issues/14436
        """
        if not self.crm_object_order:
            return None
        if config.SIMPLE_CART_MODE:
            return self.crm_object_order.delivery_cart_simple_mode
        elif self.crm_object_order.delivery_type:
            return getattr(self.crm_object_order.delivery_type, 'name', None)

    def get_order_payment_method(self) -> Optional[str]:
        """
        Для заказов через корзину. Получение метода оплаты.
        https://redmine.nastroyker.ru/issues/14436
        """
        if self.crm_object_order and self.crm_object_order.payment_method:
            return self.crm_object_order.get_payment_method_display()
