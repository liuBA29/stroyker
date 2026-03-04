from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils.functional import cached_property
from django.db import models
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from stroykerbox.apps.utils.validators import validate_svg_or_image


DISCOUNT_CHOICES = (
    ('discount', _('скидка на цену')),
    ('extra_charge', _('наценка на закупочную цену')),
)


class UserManager(BaseUserManager):
    def _create_user(self, email, password, is_staff, is_superuser, **extra_fields):
        """
        Creates and saves a User with the given username, email and password.
        """
        now = timezone.now()
        email = self.normalize_email(email)

        user = self.model(
            email=email,
            is_staff=is_staff,
            is_active=extra_fields.pop('is_active', True),
            is_superuser=is_superuser,
            last_login=now,
            date_joined=now,
            **extra_fields
        )
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        return self._create_user(email, password, False, False, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        return self._create_user(email, password, True, True, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Class implementing a fully featured User model with
    admin-compliant permissions.
    """

    DISCOUNT_CHOICES = DISCOUNT_CHOICES
    email = models.EmailField(
        _('email address'),
        unique=True,
        help_text=_(
            'Account`s unique e-mail address. Used as login for authorization.'
        ),
    )
    name = models.CharField(
        _('contact person'),
        max_length=60,
        blank=True,
        null=True,
        help_text=_('Account person name'),
    )
    company = models.CharField(
        _('company'),
        max_length=60,
        blank=True,
        null=True,
        help_text=_('Account company name'),
    )
    phone = models.CharField(
        _('phone'),
        max_length=18,
        help_text=_('Account phone number'),
        null=True,
        blank=True,
    )
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin ' 'site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=False,
        help_text=_(
            'Designates whether this user should be treated as '
            'active. Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(
        _('date joined'), auto_now_add=True, db_index=True
    )
    discount_group = models.ForeignKey(
        'UserDiscountGroup',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_('discount group'),
        related_name='users',
    )
    calculation = models.CharField(
        verbose_name=_('Вариант расчета'),
        max_length=32,
        choices=DISCOUNT_CHOICES,
        default='discount',
    )
    discount = models.SmallIntegerField(verbose_name=_('Процент'), default=0)
    personal_manager_email = models.EmailField(
        'email менеджера',
        help_text=('Email менеджера, назначенного пользователю.'),
        null=True,
        blank=True,
    )
    notify_personal_manager_only = models.BooleanField(
        'уведомления только менеджеру',
        default=False,
        help_text=('Отправлять уведомления о заказах только персональному менеджеру.'),
    )
    personal_info = models.TextField(
        'персональная информация в ЛК', blank=True, null=True
    )
    avatar = models.FileField(
        verbose_name='аватар', upload_to='avatars/',
        blank=True, null=True, validators=(validate_svg_or_image,))

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_is_active = self.is_active

    def clean(self):
        if self.email:
            self.email = self.email.lower()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @cached_property
    def display_name(self):
        return self.name or self.email

    @cached_property
    def has_discount(self):
        return bool(
            self.discount or (self.discount_group and self.discount_group.discount)
        )

    @cached_property
    def discount_percent(self):
        if self.discount:
            return self.discount
        elif self.discount_group and self.discount_group.discount:
            return self.discount_group
        return 0

    @property
    def as_dict(self):
        result = model_to_dict(self)
        return result


class UserDocument(models.Model):
    """
    A document file associated with a specific date and a specific user.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    name = models.CharField(
        _('document name'), max_length=128, help_text=_('Document`s name.')
    )
    doc_date = models.DateField(_('document date'), help_text=_('Document`s date.'))
    file = models.FileField(
        _('document file'), upload_to='users/documents', help_text=_('Document file.')
    )

    class Meta:
        ordering = ['-doc_date']
        verbose_name = _('user document')
        verbose_name_plural = _('user documents')

    def __str__(self):
        return self.name


class UserDiscountGroup(models.Model):
    """
    A user group whose members have some discounts on store products.
    """

    DISCOUNT_CHOICES = DISCOUNT_CHOICES
    name = models.CharField(_('group name'), max_length=128)
    discount = models.SmallIntegerField(_('discount percent'), default=0)
    calculation = models.CharField(
        verbose_name=_('Вариант расчета'),
        max_length=32,
        choices=DISCOUNT_CHOICES,
        default='discount',
    )

    class Meta:
        verbose_name = _('discount group')
        verbose_name_plural = _('discount groups')

    def __str__(self):
        return self.name
