from django.contrib.admin import SimpleListFilter

from .models import User


class UserManagerEmailFilter(SimpleListFilter):
    title = 'Email менеджера'
    parameter_name = 'personal_manager_email'

    def lookups(self, request, model_admin):
        qs = User.objects.values_list(
            'personal_manager_email', 'personal_manager_email'
        ).exclude(personal_manager_email__isnull=True)
        return qs.distinct()

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            queryset = queryset.filter(personal_manager_email=self.value())
        return queryset
