import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.db.models.signals import post_save
from django.core import mail
from django.conf import settings
from django.urls import reverse
from django.template import Context, Template

from model_bakery import baker
from stroykerbox.apps.crm import forms, models as crm_models
from stroykerbox.apps.crm.templatetags import crm_tags
from stroykerbox.apps.commerce import models as cart_models


class CrmGenericTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email='test_user@testmail.com',
                                                         password='test', phone='12345678912')
        self.order = baker.make(
            cart_models.Order, user=self.user, status='new')


class CrmFromCartRequestTest(CrmGenericTest):

    @mock.patch('stroykerbox.apps.crm.models.FromCartRequest.objects.create')
    def test_order_created_from_cart(self, created):
        """
        When creating a new order from the cart,
        the FromCartRequest model object should be automatically created.
        """
        self.order.from_cart = True
        self.order.save()
        post_save.send(sender=cart_models.Order,
                       instance=self.order, created=True)
        # Check that the signal is intercepted.
        self.assertEquals(1, created.call_count)

    @mock.patch('stroykerbox.apps.crm.models.FromCartRequest.objects.create')
    def test_order_created_manually(self, created):
        """
        When you create an order manually,
        the FromCartRequest model object is not created.
        """
        post_save.send(sender=cart_models.Order,
                       instance=self.order, created=True)
        self.assertEquals(0, created.call_count)


class CrmCallmeRequestTest(CrmGenericTest):

    def test_callme_request_created(self):
        """
        Message is expected to be sent to managers.
        """
        baker.make(crm_models.CallMeRequest, object_class='callmerequest')
        recipient_list = [email for _, email in settings.MANAGERS]

        self.assertEqual(1, len(mail.outbox))
        self.assertEqual(mail.outbox[0].recipients(), recipient_list)


class CrmFeedbackMessageRequestTest(CrmGenericTest):

    def test_feedback_msg_request_created(self):
        """
        Message is expected to be sent to managers.
        """
        baker.make(crm_models.FeedbackMessageRequest, object_class='feedbackmessagerequest')
        recipient_list = [email for _, email in settings.MANAGERS]
        self.assertEqual(1, len(mail.outbox))
        self.assertEqual(mail.outbox[0].recipients(), recipient_list)


class CrmFormsTest(TestCase):

    def setUp(self):
        self.feedback_msg_form_data = {'url': '/', 'name': 'some_name', 'email': 'slksls@slkdlskdls.ru',
                                       'phone': '72338882999', 'message': 'some message test', 'agree': True}
        self.callme_form_data = {'name': 'some name', 'phone': '72238882288'}

    def test_feedback_message_form_common(self):
        form = forms.FeedbackMessageForm(self.feedback_msg_form_data)

        self.assertEqual(
            0, crm_models.FeedbackMessageRequest.objects.all().count())
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(
            1, crm_models.FeedbackMessageRequest.objects.all().count())

    def test_callme_form_common(self):
        form = forms.CallMeForm(self.callme_form_data)

        self.assertEqual(0, crm_models.CallMeRequest.objects.all().count())
        self.assertTrue(form.is_valid())
        form.save()
        self.assertEqual(1, crm_models.CallMeRequest.objects.all().count())

    def test_feedback_message_form_ajax_action_url(self):
        url = reverse('crm:feedback-message-request')
        # without ajax (redirect expected)
        response = self.client.post(url, self.feedback_msg_form_data)
        self.assertEqual(302, response.status_code)

        # with ajax
        response = self.client.post(url, self.feedback_msg_form_data,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(200, response.status_code)
        self.assertEqual(response['Content-Type'], 'application/json')

        content = json.loads(response.content)
        self.assertEqual(content['success'], True)
        self.assertIsNone(content['errors'])

    def test_callme_form_on_page_ajax_action_url(self):
        url = reverse('crm:callme-request')
        # without ajax (redirect expected)
        response = self.client.post(url, self.callme_form_data)
        self.assertEqual(302, response.status_code)

        # with ajax
        response = self.client.post(url, self.callme_form_data,
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(200, response.status_code)
        self.assertEqual(response['Content-Type'], 'application/json')

        content = json.loads(response.content)
        self.assertEqual(content['success'], True)
        self.assertIsNone(content['errors'])


class CrmTagsTest(TestCase):

    def test_render_feedback_message_request_form_tag(self):
        out = Template(
            "{% load crm_tags %}"
            "{% render_feedback_message_request_form %}"
        ).render(Context())
        self.assertIn(
            'id="feedback-message-request-form"', out)

    def test_render_feedback_message_request_form_tag_as_result(self):
        result = crm_tags.render_feedback_message_request_form(Context())
        self.assertIsInstance(result['form'], forms.FeedbackMessageForm)

    def test_render_callme_request_form_tag(self):
        out = Template(
            "{% load crm_tags %}"
            "{% render_callme_request_form %}"
        ).render(Context())
        # self.assertIsInstance(self.user_cart, cart.Cart)
        self.assertIn(
            'form id="callme-request-form"', out)

    def test_render_callme_request_form_tag_as_result(self):
        result = crm_tags.render_callme_request_form(Context())
        self.assertIsInstance(result['form'], forms.CallMeForm)
