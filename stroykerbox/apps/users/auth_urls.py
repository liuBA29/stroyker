from django.urls import path
from django.contrib.auth import views as auth_views

from stroykerbox.apps.users import views as users_views

from .forms import MyPasswordResetForm

urlpatterns = [
    path('logout/', auth_views.LogoutView.as_view(template_name='registration/logout.html'), name='logout'),
    path('password/reset/', auth_views.PasswordResetView.as_view(
        form_class=MyPasswordResetForm,
        template_name='registration/password_reset.html',
        html_email_template_name='registration/email/password_reset.html'),
        name='password_reset'),
    path('password/reset/done/', auth_views.PasswordResetDoneView.as_view(),
         name='password_reset_done'),
    path('password/reset/confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/reset/complete/', auth_views.PasswordResetCompleteView.as_view(),
         name='password_reset_complete'),
]

urlpatterns += [
    path('login/', users_views.UsersLoginView.as_view(), name='login'),
    path('register/', users_views.registration, name='registration'),
    path('register/success/', users_views.registration, kwargs={'success': True},
         name='registration_success'),
    path('register/activate/', users_views.registration_activate,
         name='registration_activate'),
]
