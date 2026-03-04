from logging import getLogger

from django.utils.translation import ugettext as _
from django.utils.html import mark_safe
from django.conf import settings
from django.shortcuts import reverse
from django.contrib.auth import authenticate, login as login_user
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.http import Http404
from constance import config

from stroykerbox.apps.commerce.models import Order
from stroykerbox.settings.constants import INVOICING

from .forms import RegistrationForm, UserActivationForm, UserProfileForm, LoginForm
from .models import User


logger = getLogger(__name__)


class UsersLoginView(LoginView):
    form_class = LoginForm

    def post(self, request, *args, **kwargs):
        # hack to enable "remember me" checkbox when login
        if request.POST.get('remember_me', None):
            request.session.set_expiry(0)
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Insert the seo data to the request."""
        if hasattr(self.request, 'seo'):
            title = _('Login Page')
            self.request.seo.breadcrumbs.append((self.request.path, title))
            self.request.seo.title.append(title)
        return super().get_context_data(**kwargs)


@login_required
def profile(request):
    """
    User profile main page
    """
    if hasattr(request, 'seo'):
        title = _('Profile Main Page')
        request.seo.breadcrumbs.append((request.path, title))
        request.seo.title.append(title)

    return render(request, 'users/profile.html', {'user': request.user})


@login_required
def profile_edit(request):
    """
    User Data Change Page
    """
    form = pass_form = None

    if request.method == 'POST':
        if 'old_password' in request.POST:
            pass_form = current_form = PasswordChangeForm(request.user, request.POST)
        else:
            form = current_form = UserProfileForm(request.POST, instance=request.user)
        if current_form.is_valid():
            messages.success(request, _('Your data was successfully updated'))
            current_form.save()

    if not form:
        form = UserProfileForm(instance=request.user)
    if not pass_form:
        pass_form = PasswordChangeForm(request.user)

    if hasattr(request, 'seo'):
        title = _('Profile Page')
        request.seo.breadcrumbs += [
            (reverse('users:profile'), _('Profile')),
            (request.path, title),
        ]
        request.seo.title.append(title)

    return render(
        request,
        'users/profile_edit.html',
        {'user': request.user, 'form': form, 'pass_form': pass_form},
    )


def registration(request, success=False):
    """
    User registration view
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            account = form.save()
            if config.USERS_AUTOACTIVATION:
                msg = _(
                    'Аккаунт успешно создан.'
                    '\nСсылка на подтверждение отправлена на '
                    'указанную при регистрации почту.'
                )
                form.send_activation_email(request, account)
            else:
                msg = _(
                    'Аккаунт успешно создан.'
                    '\nДанные переданы менеджеру для активации.'
                )
                form.send_manager_activation_email(account)

            messages.success(request, msg)

            return redirect('registration_success')
    else:
        form = RegistrationForm()

    if hasattr(request, 'seo'):
        title = _('Registration Page')
        request.seo.breadcrumbs.append((request.path, title))
        request.seo.title.append(title)

    return render(
        request, 'registration/registration.html', {'form': form, 'success': success}
    )


def registration_activate(request):
    """
    User activation
    """
    user = get_object_or_404(User, email=request.GET.get('email'))
    form = UserActivationForm(request.GET, instance=user)
    if form.is_valid():
        user = form.save()
        user = authenticate(email=user.email)
        login_user(request, user)
        messages.success(request, _('Ваш аккаунт успешно активирован.'))
        return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        msg = _('Ошибка активации.')
        for f, err in form.errors.items():
            msg += f'\n{f}: {err}'
        messages.error(request, mark_safe(msg))

    return render(request, 'registration/registration_activate.html')


@login_required
def orders_list(request):
    """
    User's orders list
    """
    orders = request.user.orders.get_visible_for_user()
    years = [dt.strftime('%Y') for dt in orders.dates('created_at', 'year')]
    years.sort(reverse=True)

    orders_sum = orders.filter(status='completed').aggregate(Sum('total_price'))

    if hasattr(request, 'seo'):
        title = _('Orders')
        request.seo.breadcrumbs += [
            (reverse('users:profile'), _('Profile')),
            (request.path, title),
        ]
        request.seo.title.append(title)

    return render(
        request,
        'users/orders_list.html',
        {'orders': orders, 'years': years, 'orders_sum': orders_sum},
    )


@login_required
def order_details(request, order_pk):
    """
    User's order details
    """

    # https://redmine.nastroyker.ru/issues/16289
    if config.LK_HIDE_ORDER_DETAILS:
        raise Http404

    kwargs = {'pk': order_pk}
    if not request.user.is_staff:
        kwargs['user'] = request.user
    order = get_object_or_404(Order, **kwargs)

    if hasattr(request, 'seo'):
        request.seo.breadcrumbs += [
            (reverse('users:profile'), _('Profile')),
            (reverse('users:orders_list'), _('Orders')),
            (request.path, order),
        ]
        request.seo.title.append(str(order))

    context = {'order': order}
    if order.payment_method == INVOICING:
        context['invoice_pdf_link'] = True

    return render(request, 'users/order_details.html', context)


@login_required
def user_document_list(request, year=None, month=None):
    """
    User's documents list
    """
    docs = request.user.documents.all()
    years = [dt.strftime('%Y') for dt in docs.dates('doc_date', 'year')]

    if year:
        docs = docs.filter(doc_date__year=year)
        if month:
            docs = docs.filter(doc_date__month=month)

    if hasattr(request, 'seo'):
        title = _('Documents')
        title_date = ''
        request.seo.breadcrumbs += [
            (reverse('users:profile'), _('Profile')),
            (reverse('users:docs_index_list'), title),
        ]
        if year:
            title_date = f' ({year})'
            request.seo.breadcrumbs.append(
                (reverse('users:docs_year_list', kwargs={'year': year}), year)
            )
        if month:
            title_date = f' ({month}/{year})'
            request.seo.breadcrumbs.append(
                (
                    reverse(
                        'users:docs_month_list', kwargs={'year': year, 'month': month}
                    ),
                    month,
                )
            )

        request.seo.title.append(f'{title}{title_date}')

    return render(
        request,
        'users/userdocs-list.html',
        {'docs': docs, 'years': years, 'year': year, 'month': month},
    )
