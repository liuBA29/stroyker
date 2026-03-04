from django.views.generic import TemplateView
from django.utils.translation import ugettext as _

from .models import Question


class FaqPage(TemplateView):
    template_name = 'faq/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['questions'] = Question.objects.filter(published=True)

        if hasattr(self.request, 'seo'):
            self.request.seo.title.append(_('FAQ'))

        return context
