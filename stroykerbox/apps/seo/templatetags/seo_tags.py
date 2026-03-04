from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

from constance import config

register = template.Library()


def meta_tags(context):
    """
    Meta tags: keywords, description
    """
    request = context['request']
    if not hasattr(request, 'seo'):
        return

    keywords_overwrited = getattr(request.seo.overwrite, 'meta_keywords', None)

    description_overwrited = getattr(request.seo.overwrite, 'meta_description', None)

    keywords = keywords_overwrited or request.seo.meta_keywords or ''

    ai_keywords = (
        getattr(request.seo.overwrite, 'ai_keywords', request.seo.ai_keywords) or ''
    )

    description = description_overwrited or request.seo.meta_description or ''

    category = context.get('category', None)
    product = context.get('product', None)

    if category:
        if not description_overwrited:
            if not description:
                description = category.name
            if config.SEO_CATEGORY_META_DESC_PREFIX:
                description = f'{config.SEO_CATEGORY_META_DESC_PREFIX} {description}'

            # https://redmine.fancymedia.ru/issues/12714
            if getattr(request.seo, 'category_filter_params', None):
                params_prefix = '. '.join(request.seo.category_filter_params)
                description += f' {params_prefix}.'

            if config.SEO_CATEGORY_META_DESC_SUFFIX:
                description = f'{description} {config.SEO_CATEGORY_META_DESC_SUFFIX}'
        if not keywords_overwrited:
            if config.SEO_CATEGORY_META_KEYWORDS_DEFAULT:
                if not keywords:
                    keywords = context.get('category').name.replace(' ', ', ')
                keywords += f', {config.SEO_CATEGORY_META_KEYWORDS_DEFAULT}'

        # https://redmine.nastroyker.ru/issues/19418
        if not ai_keywords and config.SEO_CATEGORY_META_AI_KEYWORDS_DEFAULT:
            ai_keywords = config.SEO_CATEGORY_META_AI_KEYWORDS_DEFAULT
    elif product:
        if not description_overwrited:
            if not description:
                description = product.name
            if config.SEO_PRODUCT_META_DESC_PREFIX:
                description = f'{config.SEO_PRODUCT_META_DESC_PREFIX} {description}'
            if config.SEO_PRODUCT_META_DESC_SUFFIX:
                description = f'{description} {config.SEO_PRODUCT_META_DESC_SUFFIX}'
            # https://redmine.fancymedia.ru/issues/10815
            if config.SEO_PRODUCT_META_USE_SKU and getattr(product, 'sku', None):
                description = f'{product.sku} {description}'
        if not keywords_overwrited:
            if config.SEO_PRODUCT_META_KEYWORDS_DEFAULT:
                if not keywords:
                    keywords = context.get('product').name.replace(' ', ', ')
                keywords += f', {config.SEO_PRODUCT_META_KEYWORDS_DEFAULT}'

        # https://redmine.nastroyker.ru/issues/19418
        if not ai_keywords and config.SEO_PRODUCT_META_AI_KEYWORDS_DEFAULT:
            ai_keywords = config.SEO_PRODUCT_META_AI_KEYWORDS_DEFAULT

    elif not keywords_overwrited and not keywords and request.seo.title:
        keywords = ' '.join(request.seo.title).replace(' ', ', ')

    # Check if the request page is part of pagination.
    # If yes - return the canonical absolute path.
    canonical = (
        request.GET.get('page')
        and f'{request.scheme}://{request.get_host()}{request.path}'
    )

    # https://redmine.nastroyker.ru/issues/19418
    if ai_keywords:
        keywords += f', {ai_keywords}'

    return {'keywords': keywords, 'description': description, 'canonical': canonical}


@register.inclusion_tag('seo/tags/meta_tags.html', takes_context=True)
def render_meta_tags(context):
    """
    Meta tags: keywords, description
    """
    return meta_tags(context)


@register.simple_tag(takes_context=True)
def get_meta_tag(context, tag_name):
    """
    Get meta tag by name
    """
    return meta_tags(context).get(tag_name)


@register.inclusion_tag('seo/tags/breadcrumbs.html', takes_context=True)
def render_breadcrumbs(context):
    """
    Breadcrumbs
    """
    request = context['request']
    if not hasattr(request, 'seo'):
        return
    context['breadcrumbs'] = request.seo.breadcrumbs
    return context


@register.inclusion_tag('seo/tags/h1.html', takes_context=True)
def render_h1(context):
    """
    Page header in tag h1
    """
    request = context['request']
    category = context.get('category')
    product = context.get('product')
    h1 = request.seo.overwrite.h1 if request.seo.overwrite else request.seo.h1

    if category:
        h1 = h1 or category.name
        if config.SEO_CATEGORY_META_H1_PREFIX:
            h1 = f'{config.SEO_CATEGORY_META_H1_PREFIX} {h1}'
        if config.SEO_CATEGORY_META_H1_SUFFIX:
            h1 = f'{h1} {config.SEO_CATEGORY_META_H1_SUFFIX}'
    elif product:
        h1 = h1 or product.name
        if config.SEO_PRODUCT_META_H1_PREFIX:
            h1 = f'{config.SEO_PRODUCT_META_H1_PREFIX} {h1}'
        if config.SEO_PRODUCT_META_USE_SKU:
            h1 = f'{h1} {product.sku}'
        if config.SEO_PRODUCT_META_H1_SUFFIX:
            h1 = f'{h1} {config.SEO_PRODUCT_META_H1_SUFFIX}'

    context['breadcrumbs'] = request.seo.breadcrumbs
    context['h1'] = mark_safe(h1.replace(' ,', ',')) if h1 else None

    return context


@register.simple_tag(takes_context=True)
def render_title(context):
    """
    Title tag
    """
    request = context['request']
    if not hasattr(request, 'seo'):
        return

    title = request.seo.title
    if request.seo.overwrite and request.seo.overwrite.title:
        title = [request.seo.overwrite.title]
        return request.seo.title_glue.join(reversed(title))
    else:
        result = request.seo.title_glue.join(reversed(title))

        if context.get('category'):
            if config.SEO_CATEGORY_META_TITLE_PREFIX:
                result = f'{config.SEO_CATEGORY_META_TITLE_PREFIX} {result}'
            if config.SEO_CATEGORY_META_TITLE_SUFFIX:
                result = f'{result} {config.SEO_CATEGORY_META_TITLE_SUFFIX}'
        elif context.get('product'):
            if config.SEO_PRODUCT_META_TITLE_PREFIX:
                result = f'{config.SEO_PRODUCT_META_TITLE_PREFIX} {result}'
            if config.SEO_PRODUCT_META_USE_SKU:
                result = f'{result} {context["product"].sku}'
            if config.SEO_PRODUCT_META_TITLE_SUFFIX:
                result = f'{result} {config.SEO_PRODUCT_META_TITLE_SUFFIX}'

        return result


@register.inclusion_tag('seo/tags/schema_org_main.html', takes_context=True)
def schema_org_organization(context):
    context['so_name'] = config.SCHEMA_ORG_ORGANIZATION_NAME
    context['so_address'] = config.SCHEMA_ORG_ORGANIZATION_ADDRESS
    context['so_phone'] = config.SCHEMA_ORG_ORGANIZATION_PHONE
    return context


@register.inclusion_tag('seo/tags/schema_org_category.html', takes_context=True)
def schema_org_category(context):
    request = context['request']
    category = context.get('category')
    if category:
        context['so_category_name'] = category.name
        context['so_category_description'] = meta_tags(context).get('description', '')

        category_image_url = f'{settings.STATIC_URL}images/no-img.png'
        if category.image:
            category_image_url = category.image.url
        elif category.svg_image:
            category_image_url = category.svg_image.url
        elif config.CATEGORY_DEFAULT_IMAGE:
            category_image_url = f'{settings.MEDIA_URL}{config.CATEGORY_DEFAULT_IMAGE}'

        context['so_category_image'] = (
            f'{request.scheme}://{request.get_host()}{category_image_url}'
        )
    return context


@register.inclusion_tag('seo/tags/open_graph_tags.html', takes_context=True)
def open_graph_tags(context):
    request = context['request']
    category = context.get('category')
    product = context.get('product')

    og_image = f'{settings.STATIC_URL}images/no-img.png'
    try:
        if product and product.images.exists():
            og_image = product.images.first().image.url

        if category and category.image:
            og_image = category.image.url

        if config.OPEN_GRAPH_IMAGE:
            og_image = f'{settings.MEDIA_URL}{config.OPEN_GRAPH_IMAGE}'
    except Exception:
        pass

    context['og_site_name'] = config.OPEN_GRAPH_SITE_NAME
    context['og_image'] = f'{request.scheme}://{request.get_host()}{og_image}'
    context['og_url'] = (
        f'{request.scheme}://{request.get_host()}{request.get_full_path()}'
    )
    return context
