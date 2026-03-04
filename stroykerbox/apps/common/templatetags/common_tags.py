from django import template
from django.forms import Form

from constance import config

register = template.Library()


@register.inclusion_tag('common/tags/form-agreement.html')
def render_form_agreement(form: Form):
    form_name, form_hash = form.__class__.__name__.lower(), hash(form)
    context: dict[str, str | bool] = {'input_id': f'{form_name}-{form_hash}'}
    if config.SHOW_FORM_AGREEMENT_2:
        context['agreement2'] = True
    return context
