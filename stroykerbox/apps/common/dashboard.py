from typing import TypedDict
from decimal import Decimal
from datetime import datetime

from django.contrib.auth import get_user_model

from stroykerbox.apps.commerce.models import Order
from stroykerbox.apps.crm import models as crm_models
from stroykerbox.apps.subscription.models import Subscription
from stroykerbox.apps.custom_forms.models import CustomFormResult


class BaseData(TypedDict):
    id: int
    date: datetime


class CardOrderData(BaseData):
    amount: Decimal
    status: str
    is_paid: bool


class CustomFormData(BaseData):
    form_title: str


class Dashboard:
    """
    https://redmine.nastroyker.ru/issues/15676
    """

    def get_custom_forms(self) -> list[CustomFormData]:

        # upd https://redmine.nastroyker.ru/issues/18245
        qs = CustomFormResult.objects.values('pk', 'created', 'form__title')

        return [
            CustomFormData(id=i['pk'], date=i['created'], form_title=i['form__title'])
            for i in qs
        ]

    def get_subscriptions(self) -> list[BaseData]:
        qs = Subscription.objects.all()
        return [
            BaseData(id=i['pk'], date=i['created_at'])
            for i in qs.values('pk', 'created_at')
        ]

    def get_registrations(self) -> list[BaseData]:
        User = get_user_model()
        qs = User.objects.filter(is_staff=False)
        return [
            BaseData(id=i['pk'], date=i['date_joined'])
            for i in qs.values('pk', 'date_joined')
        ]

    def get_cart_orders(self) -> list[CardOrderData]:
        """заказы в корзине"""
        return [
            CardOrderData(
                id=i['pk'],
                date=i['created_at'],
                amount=i['final_price'],
                status=i['status'],
                is_paid=i['is_paid'],
            )

            # https://redmine.nastroyker.ru/issues/18245#note-4
            for i in Order.objects.values(
                'pk', 'created_at', 'final_price', 'status', 'is_paid'
            )
        ]

    def get_crm_requests(
        self, request_model: crm_models.CrmRequestBase
    ) -> list[BaseData]:
        """crm-запросы"""
        return [
            BaseData(id=i['pk'], date=i['created'])
            for i in request_model.objects.values('pk', 'created')
        ]

    def get_summary(self) -> dict[str, list]:
        output = {
            'card-orders': self.get_cart_orders(),
            # https://redmine.nastroyker.ru/issues/18245#note-4
            # 'card-orders-crm': self.get_crm_requests(
            #     request_model=crm_models.FromCartRequest
            # ),
            'feedback': self.get_crm_requests(
                request_model=crm_models.FeedbackMessageRequest
            ),
            'callme': self.get_crm_requests(request_model=crm_models.CallMeRequest),
            'gift-request': self.get_crm_requests(
                request_model=crm_models.GiftForPhoneRequest
            ),
            'registrations': self.get_registrations(),
            'subscriptions': self.get_subscriptions(),
            'custom-forms': self.get_custom_forms(),
        }
        return output  # type: ignore
