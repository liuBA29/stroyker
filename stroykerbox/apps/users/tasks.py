# from celery import shared_task
from logging import getLogger

from django.core.mail import EmailMessage
from django.urls import reverse
from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from constance import config
from django_rq import job

logger = getLogger(__name__)


@job('high')
def send_user_activation_email(user, link):
    """
    Send an activation link to a user
    """
    body = get_template('registration/email/user_activation_link.html')
    context = {'user': user, 'link': link}
    message = EmailMessage(_('Registration at %s' % config.SITE_NAME),
                           body.render(context), to=(user.email,))
    message.content_subtype = 'html'
    try:
        message.send(fail_silently=False)
    except Exception as e:
        logger.exception(e)


@job('high')
def new_registration_notify_manager(account):
    """
    Notification of new registration.
    """
    if config.MANAGER_EMAILS:
        try:
            subject = _('New registration')
            admin_link = reverse('admin:users_user_change', args=(account.pk,))
            mail_body = get_template(
                'users/email/new-registration-nofity-manager.html').render({
                    'config': config,
                    'account': account,
                    'admin_link': f'{settings.BASE_URL}{admin_link}'})

            mail = EmailMessage(subject, mail_body, config.DEFAULT_FROM_EMAIL,
                                to=[e.strip() for e in config.MANAGER_EMAILS.split(',') if e])
            mail.content_subtype = 'html'
            mail.send(fail_silently=False)
        except Exception as e:
            logger.exception(e)
        else:
            logger.debug(f'Уведомлениe о регистрации нового аккаунта {account} отправлены на email-адреса, '
                         f'указанные в настройке config.MANAGER_EMAILS: {config.MANAGER_EMAILS}')
    else:
        logger.error(
            'Не указаны email-адреса для уведомления менеджеров о новых регистрациях пользователей.')


@job('high')
def send_user_activation_notify_manager(user):
    """
    Notification of new activation (autoactivation is ON).
    """
    if config.MANAGER_EMAILS:
        try:
            subject = 'Активация аккаунта'
            admin_link = reverse('admin:users_user_change', args=(user.pk,))
            mail_body = get_template(
                'users/email/new-activation-nofity-manager.html').render({
                    'config': config,
                    'account': user,
                    'admin_link': f'{settings.BASE_URL}{admin_link}'})

            mail = EmailMessage(subject, mail_body, config.DEFAULT_FROM_EMAIL,
                                to=[e.strip() for e in config.MANAGER_EMAILS.split(',') if e])
            mail.content_subtype = 'html'
            mail.send(fail_silently=False)
        except Exception as e:
            logger.exception(e)
        else:
            logger.debug(f'Уведомления об активации нового аккаунта {user} отправлены на email-адреса, '
                         f'указанные в настройке config.MANAGER_EMAILS: {config.MANAGER_EMAILS}')
    else:
        logger.error(
            'Не указаны email-адреса для уведомления менеджеров о новых регистрациях/активациях пользователей.')


@job('high')
def send_user_activation_notify(user):
    """
    Notification of the user that his account has been activated.
    """
    body = get_template('users/email/user_activation_notify.html')
    password = None
    if not user.password:
        password = user.__class__.objects.make_random_password()
        user.set_password(password)

    context = {'user': user, 'password': password,
               'profile_link': f'{settings.BASE_URL}{reverse("users:profile")}'}
    try:
        message = EmailMessage(_('Account Activation on %s' % config.SITE_NAME),
                               body.render(context), config.DEFAULT_FROM_EMAIL,
                               to=(user.email,))
        message.content_subtype = 'html'
        message.send(fail_silently=False)
    except Exception as e:
        logger.exception(e)
    else:
        logger.debug(f'Уведомлениe о регистрации нового аккаунта {user} отправлено на email-адрес, '
                     f'указанный при регистрации: {user.email}')
