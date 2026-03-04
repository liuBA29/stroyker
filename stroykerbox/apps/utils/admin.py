from django.conf import settings
from django.contrib import admin

from import_export.admin import ImportExportModelAdmin
from import_export import resources


if 'django.contrib.redirects' in settings.INSTALLED_APPS:
    from django.contrib.redirects.models import Redirect
    from django.contrib.redirects.admin import RedirectAdmin

    class RedirectResource(resources.ModelResource):

        class Meta:
            model = Redirect
            exclude = ('id', 'site')
            import_id_fields = ('old_path', 'new_path')

        def before_save_instance(self, instance, using_transactions, dry_run):
            if not hasattr(instance, 'site'):
                instance.site_id = getattr(settings, 'SITE_ID', 1)
            return instance

    class RedirectAdminCustom(ImportExportModelAdmin, RedirectAdmin):
        resource_class = RedirectResource

    admin.site.unregister(Redirect)
    admin.site.register(Redirect, RedirectAdminCustom)

if 'django.contrib.sites' in settings.INSTALLED_APPS:
    from django.contrib.sites.models import Site
    from django.contrib.sites.admin import SiteAdmin

    class SiteAdminCustom(SiteAdmin):
        def has_delete_permission(self, request, obj=None):
            return (obj and obj.id != settings.SITE_ID)

    admin.site.unregister(Site)
    admin.site.register(Site, SiteAdminCustom)
