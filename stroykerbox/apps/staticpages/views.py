from django.http import Http404
from django.views.generic import DetailView
from django import template
from django.conf import settings
from django.core.cache import cache

from .models import Page, PageContructor


class StaticPageView(DetailView):
    context_object_name = 'page'

    def get_object(self, **kwargs):
        url = self.kwargs.get('url', None)
        if not url:
            raise AttributeError("Generic detail view %s must be called with "
                                 "either an object slug."
                                 % self.__class__.__name__)

        qs = Page.objects.filter(url=f'/{url}/')
        if not qs.exists():
            qs = PageContructor.objects.filter(url=f'/{url}/')

        if not self.request.user.is_staff:
            qs = qs.filter(published=True)

        try:
            # Get the single item from the filtered queryset
            obj = qs.get()
        except qs.model.DoesNotExist:
            raise Http404("No %(verbose_name)s found matching the query" %
                          {'verbose_name': qs.model._meta.verbose_name})
        return obj

    def get_template_names(self):
        if self.object.__class__ == PageContructor:
            template = 'staticpages/page-contructor.html'
        elif self.object.no_wrapper:
            template = 'staticpages/staticpage-nowrapper.html'
        elif self.object.container:
            template = 'staticpages/staticpage-container.html'
        else:
            template = 'staticpages/staticpage.html'

        return template

    def get_staticpage_context(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if hasattr(self.request, 'seo'):
            if self.object.parent:
                self.request.seo.breadcrumbs.append(
                    (self.object.parent.get_absolute_url(), self.object.parent.title))

        if not self.object.no_wrapper:
            context['files'] = self.object.files.all()
            context['images'] = self.object.images.all()
        return context

    def get_pageconstructor_context(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.object.cache:
            html = cache.get_or_set(
                self.object.cache_key, self.get_html_for_container_tag(context), self.object.cache_timeout)
        else:
            html = self.get_html_for_container_tag(context)

        context['html'] = html
        return context

    def get_context_data(self, **kwargs):
        context = {}
        if self.object.__class__ == Page:
            context.update(self.get_staticpage_context(**kwargs))
        elif self.object.__class__ == PageContructor:
            context.update(self.get_pageconstructor_context(**kwargs))
        else:
            context = super().get_context_data(**kwargs)

        if hasattr(self.request, 'seo'):
            if self.object.meta_keywords:
                self.request.seo.meta_keywords = self.object.meta_keywords
            if self.object.meta_description:
                self.request.seo.meta_description = self.object.meta_description

            if hasattr(self.object, 'breadcrumbs'):
                for crumb in self.object.breadcrumbs.all():
                    self.request.seo.breadcrumbs.append(
                        (crumb.link, crumb.title))
            self.request.seo.breadcrumbs.append(
                (self.request.path, self.object.title))

        self.request.seo.title.append(self.object.title)

        return context

    def get_html_for_container_tag(self, context):
        html = []
        blocks = self.object.blocks.filter(enabled=True)

        for block in blocks:
            module, tag = block.tag_line.split(':')
            load_tag_line = f'{{% load {module} %}}'
            block_args = block.args.split(',') if block.args else None

            if block_args:
                cleanded_args = ' '.join(
                    [f'"{a.strip()}"' for a in block_args])
                code_line = f'{{% {tag} {cleanded_args} %}}'
            else:
                code_line = f'{{% {tag} %}}'

            try:
                context.update({
                    'custom_block_title': block.block_title,
                    'custom_block_title_color': block.title_color,
                    'request': self.request
                })
                code = template.Template(
                    load_tag_line + code_line).render(template.Context(context))
            except Exception as e:
                if settings.DEBUG:
                    raise e
            else:
                if not code.strip():
                    continue

                tag_classes = tag.replace('render_', '')
                if tag_classes == 'statictext' and block_args:
                    tag_classes += f' {block_args[0].strip()} text-page'

                html.append({
                    'without_wrapper': block.without_wrapper,
                    'wrapper_classes': block.wrapper_classes,
                    'tag_class': tag_classes,
                    'bg_color': block.bg_color,
                    'bg_image_url': block.bg_image.url if block.bg_image else None,
                    'top_indent': block.top_indent,
                    'bottom_indent': block.bottom_indent,
                    'code': code
                })
        return html
