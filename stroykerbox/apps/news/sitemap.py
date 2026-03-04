from django.contrib.sitemaps import Sitemap

from .models import News


class NewsSitemap(Sitemap):
    changefreq = "daily"
    priority = 1.0

    def items(self):
        return News.objects.filter(published=True)

    def lastmod(self, obj):
        return obj.date
