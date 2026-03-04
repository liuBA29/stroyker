from django.contrib.sitemaps import Sitemap

from .models import Page


class PageSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Page.objects.filter(published=True).order_by('-updated_at')

    def lastmod(self, obj):
        return obj.updated_at
