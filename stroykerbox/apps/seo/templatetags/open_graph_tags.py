from django import template
from django.conf import settings

from constance import config

register = template.Library()


@register.simple_tag
def get_constance_config(key):
    return getattr(config, key)


@register.simple_tag(takes_context=True)
def get_opengraph_image(context):
    category = context.get('category')
    product = context.get('product')

    if product and product.images.exists():
        return product.images.first().image.url

    if category and category.image:
        return category.image.url

    if config.OPEN_GRAPH_IMAGE:
        return f'{settings.MEDIA_URL}{config.OPEN_GRAPH_IMAGE}'
