from django.contrib.sitemaps import Sitemap

from .models import Category, Product
from .forms import FilterForm


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return Product.objects.published()

    def lastmod(self, obj):
        return obj.updated_at


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Category.objects.filter(published=True)

    def lastmod(self, obj):
        return obj.updated


class CategoryFilterSitemap(Sitemap):
    changefreq = "weekly"

    def items(self):
        output = []
        for category in Category.objects.filter(published=True):
            form = FilterForm(category)
            category_url = category.get_absolute_url()
            url_template = '{category_url}?{key}={value}'
            for field in form:
                if hasattr(field.field, 'choices'):
                    for choice in field.field.choices:
                        if choice[0] is not None:
                            url = url_template.format(
                                category_url=category_url, key=field.name, value=choice[0])
                            output.append(url)
                            # Appends to the url one more key-value pair from other choices
                            for f in form:
                                if f != field and hasattr(f.field, 'choices'):
                                    for c in f.field.choices:
                                        if c[0] is not None:
                                            output.append(u'%s&%s' % (
                                                url, u'%s=%s' % (f.name, c[0])))
        return output

    def location(self, obj):
        return obj
