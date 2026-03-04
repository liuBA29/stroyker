from django import template
from django.utils.safestring import mark_safe
from django.template.exceptions import TemplateSyntaxError
from constance import config

from stroykerbox.apps.custom_forms.models import CustomForm
from stroykerbox.apps.custom_forms.forms import CFForm


register = template.Library()


@register.inclusion_tag('custom_forms/tags/custom_form.html', takes_context=True)
def custom_form(context, key):
    try:
        custom_form_obj = CustomForm.objects.get(key=key, active=True)
    except CustomForm.DoesNotExist:
        return

    context['form'] = CFForm(custom_form_obj)
    context['current_path'] = context['request'].path
    context['metrika_goal_name'] = custom_form_obj.metrica_goal or config.YMETRICA_GOAL_CUSTOMFORM_DEFAULT
    return context


def get_context(max_depth=4):
    import inspect
    stack = inspect.stack()[2:max_depth]
    context = {}
    for frame_info in stack:
        frame = frame_info[0]
        arg_info = inspect.getargvalues(frame)
        if 'context' in arg_info.locals:
            context = arg_info.locals['context']
            break
    return context


@register.filter
def custom_form_inside(text):
    curr_context = get_context()
    context = template.Context(curr_context)
    try:
        output = template.Template(
            '{% load custom_form_tags %}' + text).render(template.Context(context))
    except TemplateSyntaxError:
        output = text
    return mark_safe(output)


@register.filter
def is_list(value):
    return isinstance(value, list)
