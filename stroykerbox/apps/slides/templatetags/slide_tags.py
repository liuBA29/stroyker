from django import template

from stroykerbox.apps.slides.models import BigSlide, PartnerSlide, SliderSet
from constance import config

register = template.Library()


@register.inclusion_tag('big_banners/big-banners-base.html', takes_context=True)
def render_big_banners(context):
    bb_qs = BigSlide.objects.filter(published=True)
    bb_with_context_qs = bb_qs.exclude(content='').exclude(content__isnull=True)

    has_content = bb_with_context_qs.exists()
    if has_content:
        bb_qs = bb_with_context_qs
    context['big_banners'] = bb_qs
    context['has_content'] = has_content
    # context['slides_timeout'] = config.SLIDES_BIG_SLIDES_TIMEOUT
    context['show_dots'] = bb_qs.count() > 1
    context['template'] = f'big_banners/bb-mode-{config.BB_DISPLAY_MODE}.html'
    return context


@register.inclusion_tag('slides/tags/big_slides.html', takes_context=True)
def render_big_slides(context, wide_mode=False):
    slides_qs = BigSlide.objects.filter(published=True)
    slides_with_contect_qs = slides_qs.exclude(content='').exclude(content__isnull=True)
    has_content = slides_with_contect_qs.exists()
    if has_content:
        slides_qs = slides_with_contect_qs
    context['slides'] = slides_qs
    context['has_content'] = has_content
    context['slides_timeout'] = config.SLIDES_BIG_SLIDES_TIMEOUT
    context['wide_mode'] = wide_mode
    context['show_dots'] = slides_qs.count() > 1
    return context


@register.inclusion_tag('slides/tags/partner_slides.html', takes_context=True)
def render_partner_slides(context):
    slides = PartnerSlide.objects.filter(published=True)
    slides_timeout = config.SLIDES_BIG_SLIDES_TIMEOUT
    context.update({'slides': slides, 'slides_timeout': slides_timeout})
    return context


@register.inclusion_tag('slides/tags/sliderset.html', takes_context=True)
def render_sliderset(context, key):
    try:
        slider_set = SliderSet.objects.get(key=key)
    except SliderSet.DoesNotExist:
        return

    context.update({
        'sliderset': slider_set,
        'slides': slider_set.sliderset_items.all()
    })
    return context
