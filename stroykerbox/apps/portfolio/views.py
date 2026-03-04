from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.shortcuts import reverse
from django.core.exceptions import PermissionDenied
from constance import config


from .models import Portfolio


class PortfolioCheckPermMixin:
    def get(self, request, *args, **kwargs):
        if config.PORTFOLIO_STAFF_ONLY_ACCESS and not request.user.is_staff:
            raise PermissionDenied
        return super().get(request, *args, **kwargs)  # type: ignore


class PortfolioDetail(PortfolioCheckPermMixin, DetailView):
    model = Portfolio
    template_name = 'portfolio/detail.html'
    context_object_name = 'item'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context['portfolio_other'] = Portfolio.objects.filter(
            published=True, category=obj.category
        ).exclude(pk=obj.pk)

        if hasattr(self.request, 'seo'):
            self.request.seo.breadcrumbs.append(
                (reverse('portfolio:list'), 'Портфолио')
            )
            self.request.seo.breadcrumbs.append(('', obj.name))
            self.request.seo.title.append(obj.name)
        return context

    def get_queryset(self):
        return super().get_queryset().filter(published=True)


class PortfolioList(PortfolioCheckPermMixin, ListView):
    model = Portfolio
    template_name = 'portfolio/list.html'
    context_object_name = 'items'

    def get_paginate_by(self, queryset):
        return config.PORTFOLIO_ITEMS_PER_PAGE

    def get_queryset(self):
        qs = super().get_queryset()
        if category_slug := self.request.GET.get('category'):
            qs = qs.filter(category__slug=category_slug)
        return qs.exclude(published=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_category_slug'] = self.request.GET.get('category')
        context['portfolio_categories'] = (
            Portfolio.objects.order_by('category_id')
            .values('category__slug', 'category__name')
            .distinct('category_id')
        )

        if hasattr(self.request, 'seo'):
            self.request.seo.breadcrumbs.append(('', 'Портфолио'))
            self.request.seo.title.append('Список портфолио')
        return context
