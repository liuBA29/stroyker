from typing import Optional

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.utils.translation import ugettext_lazy as _

from .models import User, UserDocument, UserDiscountGroup
from .admin_filters import UserManagerEmailFilter


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""

    password1 = forms.CharField(label=_('Password'), widget=forms.PasswordInput)
    password2 = forms.CharField(
        label=_('Password confirmation'), widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = '__all__'

    def clean_password2(self) -> str:
        # Check that the two password entries match
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(_("Passwords don't match"))
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super(UserCreationForm, self).save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    password hash display field.
    """

    password = ReadOnlyPasswordHashField(
        label=_('Password'),
        help_text=_(
            'Raw passwords are not stored, so there is no way to see '
            "this user's password, but you can change the password "
            'using <a href="../password/">this form</a>.'
        ),
    )

    class Meta:
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[
            'email'
        ].help_text += (
            '</br><strong>При сохранении будет приобразован в нижний регистр.</strong>'
        )

    def clean_email(self) -> Optional[str]:
        if email := self.initial.get('email'):
            return email.lower()

    def clean_password(self) -> Optional[str]:
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        password = self.initial.get('password')
        return password


class UserDocumentAdmin(admin.ModelAdmin):
    date_hierarchy = 'doc_date'
    list_display = ('user', 'name', 'doc_date')
    list_filter = ('user', 'doc_date')


@admin.action(description='Активировать')
def set_active(modeladmin, request, queryset):
    queryset.filter(is_active=False).update(is_active=True)


@admin.action(description='Сделать неактивными')
def unset_active(modeladmin, request, queryset):
    queryset.filter(is_active=True).update(is_active=False)


class CustomUserAdmin(UserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = (
        'email',
        'company',
        'name',
        'phone',
        'discount',
        'calculation',
        'discount_group',
        'is_active',
        'date_joined',
        'last_login',
    )
    list_filter = ('is_active', 'date_joined', UserManagerEmailFilter)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (
            _('Personal info'),
            {
                'fields': (
                    'avatar',
                    'name',
                    'phone',
                    'company',
                    ('discount', 'calculation'),
                    'discount_group',
                    'personal_info',
                )
            },
        ),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (
            _('Permissions'),
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        (
            'Персональный менеджер',
            {
                'fields': (
                    'personal_manager_email',
                    'notify_personal_manager_only',
                )
            },
        ),
    )
    readonly_fields = ('date_joined', 'last_login')
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'password1', 'password2')}),
    )
    search_fields = (
        'email',
        'name',
        'phone',
        'company',
    )
    ordering = ('date_joined',)
    filter_horizontal = (
        'groups',
        'user_permissions',
    )
    actions = (set_active, unset_active)


class UserDiscountGroupAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'discount',
        'calculation',
    )


admin.site.register(User, CustomUserAdmin)
admin.site.register(UserDocument, UserDocumentAdmin)
admin.site.register(UserDiscountGroup, UserDiscountGroupAdmin)
