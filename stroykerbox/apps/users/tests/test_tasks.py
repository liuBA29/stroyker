from unittest import mock

from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core import mail

from stroykerbox.apps.users import tasks, forms


class UserTasksTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.active_user = get_user_model().objects.create_user(email='active_user@testmail.com',
                                                               password='test1', phone='12345678912',
                                                               is_active=True)
        cls.inactive_user = get_user_model().objects.create_user(email='inactive_user@testmail.com',
                                                                 password='test2', phone='12245678912',
                                                                 is_active=False)

    def test_send_user_activation_email_task_added(self):
        request = self.factory.get('/')
        with mock.patch('stroykerbox.apps.users.tasks.send_user_activation_email.delay') as patch_mock:
            forms.RegistrationForm.send_activation_email(
                request, self.active_user)
        self.assertTrue(patch_mock.called)

    def test_send_user_activation_email_task_email_send(self):
        tasks.send_user_activation_email(self.active_user, '')
        self.assertEqual(len(mail.outbox), 1)

    def test_send_user_activation_notify_task_added(self):
        with mock.patch('stroykerbox.apps.users.tasks.send_user_activation_notify.delay') as patch_mock:
            # start notification when the user becomes active
            self.inactive_user.is_active = True
            self.inactive_user.save()
        self.assertTrue(patch_mock.called)

    def test_send_user_activation_notify_task_email_send(self):
        tasks.send_user_activation_notify(self.active_user)
        self.assertEqual(len(mail.outbox), 1)

    def test_user_activation_with_password_creation(self):
        user_without_pass = get_user_model().objects.create_user(email='user@testmail.com',
                                                                 phone='12345678912')
        self.assertFalse(user_without_pass.password)
        tasks.send_user_activation_notify(user_without_pass)
        self.assertEqual(len(mail.outbox), 1)
        self.assertTrue(user_without_pass.password)
