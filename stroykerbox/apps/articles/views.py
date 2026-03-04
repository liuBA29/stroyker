from django.shortcuts import reverse
from django.views.generic.list import ListView
from django.views.generic import DetailView
from constance import config

from .models import Article


class ArticleList(ListView):
    """
    List of paginated articles.
    """
    model = Article
    template_name = 'articles/article-list.html'
    context_object_name = 'articles'
    queryset = Article.objects.filter(published=True)
    paginate_by = config.NEWS_PER_PAGE

    def get_context_data(self, **kwargs):
        if hasattr(self.request, 'seo'):
            self.request.seo.breadcrumbs.append(
                (self.request.path, config.ARTICLES_SECTION_NAME))
            self.request.seo.title.append(config.ARTICLES_SECTION_NAME)
        return super().get_context_data(**kwargs)


class ArticleDetails(DetailView):
    """
    Page of a single article.
    """
    model = Article
    template_name = 'articles/article-details.html'
    context_object_name = 'article'
    queryset = Article.objects.filter(published=True)

    def get_context_data(self, **kwargs):
        if hasattr(self.request, 'seo'):
            self.request.seo.breadcrumbs.append(
                (reverse('articles:article-list'), config.ARTICLES_SECTION_NAME))
            self.request.seo.breadcrumbs.append(
                (self.request.path, self.object.title))
            self.request.seo.title.append(self.object.title)

            if self.object.meta_keywords:
                self.request.seo.meta_keywords = self.object.meta_keywords
            if self.object.meta_description:
                self.request.seo.meta_description = self.object.meta_description

        return super().get_context_data(**kwargs)
