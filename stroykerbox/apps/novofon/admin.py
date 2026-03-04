from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.urls import path, reverse
from django.http import HttpResponseRedirect

from .models import NovofonCall, DISPOSITION_CHOICES
from .helper import Novofon, novofon_enabled


@admin.register(NovofonCall)
class NovofonCalldmin(admin.ModelAdmin):
    list_display = ('id', 'call_dt', 'number_from',
                    'number_to', 'call_type', 'disposition_ext')
    list_filter = ('call_type',)

    change_list_template = 'novofon/admin/calls_changelist.html'

    def disposition_ext(self, obj=None):
        if obj:
            return DISPOSITION_CHOICES.get(obj.disposition, '')
        return ''
    disposition_ext.short_description = 'статус звонка'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['novofon_enabled'] = novofon_enabled()
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        return [
            path('update_novofon_stats/', self.update_novofon_stats,
                 name='update_novofon_stats'),
        ] + urls

    def update_novofon_stats(self, request):
        calls_count = NovofonCall.objects.count()
        Novofon().process_stats()
        new_calls = NovofonCall.objects.count() - calls_count
        msg = _('Новых звонков: %(new_calls)s') % {'new_calls': new_calls}
        self.message_user(request, msg)
        return HttpResponseRedirect(reverse('admin:novofon_novofoncall_changelist'))
