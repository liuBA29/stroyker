import json
from typing import Any, Optional

from django.apps import apps
from django.views.generic import TemplateView
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.conf import settings
from constance import config


from .services.checker import CommonChecker
from .dashboard import Dashboard


@method_decorator(staff_member_required, name='dispatch')
class StaffCheckPage(TemplateView):
    """
    http://redmine.fancymedia.ru/issues/13347#change-79179
    """

    template_name = 'check_page/index.html'

    # https://redmine.nastroyker.ru/issues/16500#note-5
    MIN_POINTS_FOR_SUCCESS = 8

    def get_frontpage_info_block_context(self) -> dict[str, Any]:
        """
        - главная теги - h1 h2 title description keywords (вывести указанные теги с главной страницы,
            заголовки спарсить, т.к. могут быть где угодно на странице)
        """
        checker = self.checker
        return {
            'h1': checker.frontpage_h1 or '',
            'h2': checker.frontpage_h2 or '',
            'title': checker.frontpage_title or '',
            'description': checker.frontpage_description or '',
            'keywords': checker.frontpage_keywords or '',
            'ai_keywords': checker.get_frontpage_ai_keywords(),
        }

    def get_common_settings_block_context(self) -> dict[str, Any]:
        """
        1. общие настройки
        - кол-во статичных страниц
        - кол-во новостей/акций
        - SITE_NAME (вывести значение)
        - MANAGER_EMAILS (есть/нет)

        - минимум 1 запись в “контактах” (есть/нет)
        - favicon загружен (да/нет)
        - robots.txt (есть/нет)
        - яндекс метрика (есть/нет, нужно парсить наличие счетчика, не просто факт заполнения поля в настройках)
        - тг бот (есть/нет - не дефолтный)
        """
        checker = self.checker
        return {
            'sites_check': checker.sites_check,
            'staticpage_count': checker.staticpage_count,
            'news_actions_count': checker.news_actions_count,
            'contact_minimum': checker.check_contact_minimum,
            'has_robots_txt': checker.check_robots_txt,
            'yandex_metrika': checker.check_yandex_metrika,
            'telebot': checker.check_telebot,
            'parser_errors': checker.parser.errors,
            'has_favicon': config.FAVICON_FILE,
            'site_name': config.SITE_NAME or '',
            'manager_emails': config.MANAGER_EMAILS,
        }

    def get_products_data_by_category(
        self, product_published: Optional[bool] = None
    ) -> dict:
        output = dict()
        try:
            Category = apps.get_model('catalog.Category')
        except Exception:
            return dict()
        else:
            qs = Category.objects.values_list('id', 'name')
            for cat_id, name in qs:
                output[name] = self.checker.get_products_summary(
                    cat_id, published=product_published
                )
        return output

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.checker = CommonChecker()
        context['frontpage_info'] = self.get_frontpage_info_block_context()
        context['common_settings'] = self.get_common_settings_block_context()
        context['categories_summary'] = self.checker.categories_report_summary
        context['categories_published'] = self.checker.categories_report_published
        context['categories_unpublished'] = self.checker.categories_report_unpublished
        context['products_published'] = self.checker.products_published_stats
        context['products_unpublished'] = self.checker.products_unpublished_stats
        context['products_published_by_category'] = self.get_products_data_by_category(
            True
        )
        context['products_unpublished_by_category'] = (
            self.get_products_data_by_category(False)
        )
        context['project'] = settings.BASE_URL.split('//')[-1]

        # https://redmine.nastroyker.ru/issues/16500
        context['common_settings_points'] = (
            self.checker.calculate_common_settings_points
        )
        context['categories_points'] = self.checker.calculate_categories_points
        context['product_points'] = self.checker.calculate_product_points

        context['summary_point'] = self.checker.calculate_summary_point()
        # https://redmine.nastroyker.ru/issues/16500#note-5
        context['summary_point_is_success'] = bool(
            context['summary_point'] >= self.MIN_POINTS_FOR_SUCCESS
        )

        return context


@method_decorator(staff_member_required, name='dispatch')
class DashboardPage(TemplateView):
    template_name = 'common/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        self.dashboard = Dashboard()
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['json_summary'] = json.dumps(
            self.dashboard.get_summary(), default=str, indent=4, ensure_ascii=False
        )
        return context
