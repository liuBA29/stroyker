from django.contrib import admin
from django.urls import path, reverse
from django.template.response import TemplateResponse
from django.shortcuts import redirect
from django.core.management import call_command
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _

from import_export.admin import ExportMixin

from constance import config
import requests

from .models import VKCategory, VKProductMembership


class VKAdmin(admin.ModelAdmin):
    change_list_template = 'vk_market/admin/vk_changelist.html'

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('vk-get-code/', self.admin_site.admin_view(self.vk_get_code),
                 name='vk_get_code'),
            path('vk-result/', self.admin_site.admin_view(self.vk_result_page),
                 name='vk_result_page'),
            path('vk-update-categories/', self.admin_site.admin_view(self.vk_update_categories),
                 name='vk_update_categories'),
        ]
        return my_urls + urls

    def vk_update_categories(self, request):
        output = call_command('update_vk_categories', verbosity=1)

        if output:
            self.message_user(request, output)

        return HttpResponseRedirect(
            reverse('admin:vk_market_vkcategory_changelist'))

    def vk_result_page(self, request):
        code = request.GET.get('code')
        token_json = self.get_access_token(request, code).json()
        token = token_json.get('access_token')
        success = None
        if token:
            success = True
            call_command('constance', 'set', 'VK_MARKET_ACCESS_TOKEN', token)

        context = dict(
            self.admin_site.each_context(request),
            success=success,
            token_json=token_json,
            expires=token_json.get('expires_in')
        )
        return TemplateResponse(request, 'vk_market/admin/custom-page.html', context)

    def get_access_token(self, request, code):
        vk_url = 'https://oauth.vk.com/access_token'
        redirect_uri = request.build_absolute_uri(
            reverse('admin:vk_result_page'))
        params = {
            'client_id': config.VK_MARKET_APP_ID,
            'client_secret': config.VK_MARKET_SECRET_KEY,
            'redirect_uri': redirect_uri,
            'code': code,
        }
        return requests.get(vk_url, params=params)

    def vk_get_code(self, request):
        redirect_uri = request.build_absolute_uri(
            reverse('admin:vk_result_page'))
        auth_url = 'https://oauth.vk.com/authorize'
        auth_url += f'?client_id={config.VK_MARKET_APP_ID}'
        auth_url += f'&redirect_uri={redirect_uri}'
        auth_url += '&response_type=code'
        auth_url += '&scope=market,photos,offline'
        return redirect(auth_url)


@admin.register(VKCategory)
class VKCategoryAdmin(ExportMixin, VKAdmin):
    list_display = ('name', 'section_name')
    readonly_fields = ('section_id',)
    change_list_template = 'vk_market/admin/vk_categories_changelist.html'


@admin.register(VKProductMembership)
class VKProductMembershipAdmin(VKAdmin):
    list_display = ('product', 'vk_id', 'product_id', 'sku')

    @admin.display(empty_value='', description=_('Артикул'))
    def sku(self, obj):
        return obj.product.sku
