from django import template

register = template.Library()


@register.inclusion_tag('search/tags/search-form.html', takes_context=True)
def render_search_form(context, mobile=None, icon_position=None, **kwargs):
    context['mobile'] = mobile
    context['icon_position'] = icon_position or 'right'
    context['box_class'] = kwargs.get('box_class', 'general--width')
    context['input_box_class'] = kwargs.get('input_box_class')
    return context
