from django.utils.translation import ugettext as _
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.shortcuts import get_object_or_404, render
from django.shortcuts import reverse

from constance import config

from .models import News, NEWS_POST_TYPE_PROMO


def item_list(request, post_type=None):

    qs = News.objects.filter(published=True).order_by('-date')
    if post_type:
        qs = qs.filter(post_type=post_type)

    template = 'news/news-and-promo-list.html'

    main_item = qs.first()

    try:
        items_qs = qs.exclude(pk=main_item.pk)
    except AttributeError:
        items_qs = None

    page = request.GET.get('page', 1)

    if items_qs:
        sorting = request.GET.get('sorting', 'desc')
        if sorting == 'asc':
            items_qs = items_qs.order_by('date')

        paginator = Paginator(items_qs, config.NEWS_PER_PAGE)

        try:
            items = paginator.page(page)
        except PageNotAnInteger:
            page = 1
            # If page is not an integer, deliver first page.
            items = paginator.page(page)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of
            # results.
            items = paginator.page(paginator.num_pages)
            page = paginator.num_pages
    else:
        items = []

    if hasattr(request, 'seo'):
        if post_type:
            crumb_name = _('Promos List') if post_type == NEWS_POST_TYPE_PROMO else _(
                'News List')
        else:
            crumb_name = _('News and Promos')
        request.seo.breadcrumbs.append((request.path, crumb_name))
        request.seo.title.append(crumb_name)

    return render(request, template, {'main_item': main_item, 'items': items, 'page': int(page)})


def item_details(request, post_type, slug):
    item = get_object_or_404(
        News, slug=slug, post_type=post_type, published=True)
    files = item.files.all()
    images = item.images.all()

    template = 'news/item_details.html'

    if hasattr(request, 'seo'):
        if post_type == NEWS_POST_TYPE_PROMO:
            request.seo.breadcrumbs.append(
                (reverse('news:promo_list'), _('Promos')))
        else:
            request.seo.breadcrumbs.append(
                (reverse('news:news_list'), _('News')))
        request.seo.breadcrumbs.append((request.path, item.title))
        request.seo.title.append(item.title)

        if item.meta_keywords:
            request.seo.meta_keywords = item.meta_keywords
        if item.meta_description:
            request.seo.meta_description = item.meta_description

    return render(request, template, {'item': item, 'post_type': post_type,
                                      'files': files, 'images': images})
