from django import template


register = template.Library()


@register.inclusion_tag('users/tags/user-lk-link.html', takes_context=True)
def render_user_lk_link(context, mobile_mode=None):
    context['mobile_mode'] = mobile_mode
    return context


@register.inclusion_tag('users/tags/user-avatar.html')
def render_user_avatar(user):
    context = {'avatar': getattr(user, 'avatar', None)}
    return context
