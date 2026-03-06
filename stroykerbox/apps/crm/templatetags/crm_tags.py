from constance import config
from django import template
from django.template.loader import render_to_string
from django.utils.html import mark_safe
from django.utils.translation import ugettext_lazy as _

from stroykerbox.apps.crm.forms import FeedbackMessageForm, CallMeForm, GiftForPhoneRequestForm

register = template.Library()


@register.inclusion_tag('crm/tags/feedback-message-request-form.html', takes_context=True)
def render_feedback_message_request_form(context, heading_tag=None):
    context['form'] = FeedbackMessageForm()
    context['heading_tag'] = heading_tag
    return context


@register.inclusion_tag('crm/tags/feedback-form-section.html', takes_context=True)
def render_feedback_form_section(context, heading_tag=None):
    context['form'] = FeedbackMessageForm()
    context['heading_tag'] = heading_tag
    return context


@register.inclusion_tag('crm/tags/feedback-form-section-8march.html', takes_context=True)
def render_feedback_form_section_8march(context):
    context['form'] = FeedbackMessageForm()
    return context


@register.simple_tag(takes_context=True)
def render_callme_request_form(context, mobile=False):
    if config.AMOCRM_CALLME_FORM:
        html = config.AMOCRM_CALLME_FORM
        # Чтобы модалка открывалась по data-src="#callme-modal" (хедер/футер), нужен элемент с этим id.
        # Если в HTML заказчика уже есть — не трогаем. Если нет — оборачиваем в один div, не меняя содержимое.
        if 'id="callme-modal"' not in html and "id='callme-modal'" not in html:
            html = '<div id="callme-modal" class="modal">' + html + '</div>'
        return mark_safe(html)
    request = context.get('request')
    is_8march = request and '/8march_design/' in (getattr(request, 'path', '') or '')
    # На странице 8 марта не показываем нашу форму — только форма заказчика из конфига. Пустой div, чтобы кнопка не ломалась.
    if is_8march:
        return mark_safe('<div id="callme-modal" class="modal" style="display:none;" aria-hidden="true"></div>')
    context['callme_form'] = CallMeForm()
    context['mobile_mode'] = mobile
    return render_to_string('crm/tags/callme-request-form.html', context.flatten(), request=context.request)


@register.inclusion_tag('crm/tags/gift-for-phone-block.html', takes_context=True)
def render_gift_for_phone_block(context):
    if config.GIFT_FOR_PHONE_BLOCK_ENABLED and config.GIFT_FOR_PHONE_BLOCK_FILE:
        context['form'] = GiftForPhoneRequestForm(
            initial={'name': _('No Name')})
    return context
