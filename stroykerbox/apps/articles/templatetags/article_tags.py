from django import template

from stroykerbox.apps.articles.models import Article

register = template.Library()


@register.inclusion_tag('articles/tags/articles-slider.html')
def render_articles_slider(limit=12):
    articles = Article.objects.filter(published=True)
    return {'articles': articles[:limit]}


@register.inclusion_tag('articles/tags/related-articles.html', takes_context=True)
def render_related_articles(context, limit=7):
    article = context.get('article')
    if article:
        context['items'] = Article.objects.filter(published=True).exclude(pk=article.pk)[:limit]
        return context


@register.inclusion_tag('articles/tags/related-products.html', takes_context=True)
def render_article_related_products(context, article):
    context['article'] = article
    return context


@register.inclusion_tag('articles/tags/other-articles-slider.html', takes_context=True)
def render_other_articles_slider(context, article, limit=8):
    context['articles'] = Article.objects.filter(published=True).exclude(pk=article.pk)[:limit]
    return context
