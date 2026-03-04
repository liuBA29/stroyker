from functools import wraps

from django import template
from django.conf import settings
from constance import config

from stroykerbox.apps.statictext.models import Statictext

register = template.Library()


def with_as(f):
    """
    Decorator enabling a simple template tag to support "as my_var"
    syntax. When an as varible specified the result is added to the
    context under the variable name.
    """

    @wraps(f)
    def new_f(parser, token):
        contents = token.split_contents()

        if len(contents) < 3 or contents[-2] != 'as':
            return f(parser, token)

        as_var = contents[-1]
        # Remove 'as var_name' part from token
        token.contents = ' '.join(contents[:-2])
        node = f(parser, token)
        patch_node(node, as_var)
        return node

    return new_f


def patch_node(node, as_var):
    """
    Patch the render method of node to silently update the context.
    """
    node._old_render = node.render

    # We patch a bound method, so self is not required
    @wraps(node._old_render)
    def new_render(context):
        context[as_var] = node._old_render(context)
        return ''

    node.render = new_render


@register.tag()
@with_as
def render_statictext_var(parser, token):
    """
    Returns static text from db for the required key.
    With the ability to save the result in a variable.
    """
    contents = token.split_contents()
    key = contents[1][1:-1]

    try:
        statictext = Statictext.objects.get(key=key)
        return TextNode(statictext.text)
    except Statictext.DoesNotExist:
        if settings.DEBUG:
            raise
        else:
            return TextNode('')


class TextNode(template.Node):
    def __init__(self, text):
        self.text = text

    def render(self, context):
        return self.text


@register.inclusion_tag('statictext/tags/statictext-base.html', takes_context=True)
def render_statictext(context, key, cache=True):
    """
    Returns static text.
    """
    template = 'statictext/tags/statictext-empty.html'
    try:
        object = Statictext.objects.get(key=key)
    except Statictext.DoesNotExist:
        pass
    else:
        context['object'] = object
        if object.use_custom_form:
            template = 'statictext/tags/statictext-custom-form.html'
        else:
            template = 'statictext/tags/statictext.html'

    context['template'] = template
    if cache:
        context['use_cache'] = True
        context['cache_timeout'] = config.STATICTEXT_CACHE_TIMEOUT

    return context
