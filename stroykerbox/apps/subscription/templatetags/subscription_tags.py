from django import template

from stroykerbox.apps.subscription.forms import SubscriptionForm


register = template.Library()


@register.inclusion_tag('subscription/tags/footer-subscription-form.html', takes_context=True)
def render_footer_subscription_form(context):
    context['form'] = SubscriptionForm()
    return context
