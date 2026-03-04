from django import template

from stroykerbox.apps.menu.models import Menu, CustomNavigation


register = template.Library()


@register.inclusion_tag('menu/tags/menu.html')
def render_menu(menu_key, show_title=False, mmenu_mode=False):
    context = {
        'menu': Menu.objects.filter(key=menu_key).prefetch_related().first(),
        'show_title': show_title,
        'mmenu_mode': mmenu_mode
    }
    return context


@register.inclusion_tag('menu/tags/custom-navigation.html', takes_context=True)
def render_custom_navigation(context, key, show_title=False):
    try:
        nav = CustomNavigation.objects.prefetch_related(
            'links').get(key=key, published=True)
        context['nav'] = nav
        context['links'] = nav.links.all()
        context['show_title'] = show_title
    except CustomNavigation.DoesNotExist:
        pass
    return context
