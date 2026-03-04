from django import template

from stroykerbox.apps.news.models import News

register = template.Library()


@register.inclusion_tag('news/tags/teaser.html', takes_context=True)
def render_news_teaser(context):
    context['news'] = News.objects.all()[:5]
    return context


@register.inclusion_tag('news/tags/news-slider.html')
def render_news_slider(limit=9):
    return {'news': News.objects.filter(published=True)[:limit]}


@register.inclusion_tag('news/tags/related-news.html', takes_context=True)
def render_related_news(context, limit=7):
    news_item = context.get('item')
    if news_item:
        context['items'] = News.objects.filter(
            published=True, post_type=news_item.post_type).exclude(pk=news_item.pk)[:limit]
        return context
