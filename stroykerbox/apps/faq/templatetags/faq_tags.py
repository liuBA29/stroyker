from django import template

from stroykerbox.apps.faq.models import Question

register = template.Library()


@register.inclusion_tag('faq/tags/faq-frontpage-block.html', takes_context=True)
def render_faq_frontpage_block(context, limit=0):
    questions = Question.objects.filter(published=True, frontpage=True)
    if limit:
        questions = questions[:limit]
    context['questions'] = questions
    return context
