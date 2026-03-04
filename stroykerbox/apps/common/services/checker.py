from typing import Optional, Any

from django.apps import apps

from django.utils.functional import cached_property
from django.db.models.functions import Length
from django.db.models import Case, When, Value, Sum, Count, Max, Q
from django.conf import settings
from constance import config

from stroykerbox.apps.catalog.models import Category, Product, ProductImage
from stroykerbox.apps.seo.models import MetaTag
from stroykerbox.apps.telebot.helpers import telebot_is_active

from .frontpage_parser import FrontpageParser


class CommonChecker:
    CATEGORIES_POINT_HAS_IMAGE_COEFF = 0.2
    CATEGORIES_POINT_HAS_SEOTEXT_COEFF = 0.6
    CATEGORIES_POINT_HAS_TOP_PROD_COEFF = 0.1
    CATEGORIES_POINT_HAS_RELATED_COEFF = 0.1

    # https://redmine.nastroyker.ru/issues/18678
    PRODUCTS_POINT_HAS_IMG_COEFF = 0.4
    PRODUCTS_POINT_MIN_3_IMG_COEFF = 0.1

    PRODUCTS_POINT_HAS_PARAMS_COEFF = 0.4
    PRODUCTS_POINT_HAS_RELATED_COEFF = 0.1
    PRODUCTS_BIG_IMG_MINUS_VALUE = 2

    MAX_ALLOWED_IMG_SIZE_MB = 1

    EXT_KB = 'Кб'
    EXT_MB = 'Mб'
    EXT_GB = 'Гб'

    def __init__(self):
        self.parser = FrontpageParser()
        self.parser_errors = list()
        self.parsed_data = self._get_parsed_data()

    def _get_parsed_data(self) -> dict:
        self.parser.parse()
        self.parser_errors = self.parser.errors
        return self.parser.parsed_data or dict()

    def get_max_product_img_size(
        self,
        category_id: Optional[int] = None,
        published_product_status: Optional[bool] = None,
    ) -> tuple[int | float, str]:
        qs = ProductImage.objects.all()
        if published_product_status is not None:
            qs = qs.filter(product__published=published_product_status)
        if category_id:
            qs = qs.filter(product__categories__id=category_id)
        qs = qs.aggregate(max_size=Max('image_file_size'))

        size = qs.get('max_size') or 0
        ext = ''

        if size:
            if size < 512000:
                size /= 1024.0
                ext = self.EXT_KB
            elif size < 4194304000:
                size /= 1048576.0
                ext = self.EXT_MB
            else:
                size /= 1073741824.0
                ext = self.EXT_GB
        return round(size, 1), ext

    def get_products_summary(
        self, category_id: Optional[int] = None, published: Optional[bool] = None
    ) -> dict[str, int]:
        all_qs = Product.objects.all()

        if published is not None:
            all_qs = all_qs.filter(published=published)
        if category_id:
            all_qs = all_qs.filter(categories__id=category_id)

        count = all_qs.count()

        if count:
            all_qs = all_qs.select_related('images', 'params', 'props', 'related')

            qs = all_qs.annotate(
                descr_length=Length('description'),
                descr500=Case(When(descr_length__gte=500, then=Value(1)), default=0),
                has_descr=Case(When(descr_length__gte=0, then=Value(1)), default=0),
                img_count=Count('images'),
                has_img=Case(When(img_count__gt=0, then=Value(1)), default=0),
                has_img3=Case(When(img_count__gte=3, then=Value(1)), default=0),
                has_params=Case(When(params__isnull=False, then=Value(1)), default=0),
                has_props=Case(When(props__isnull=False, then=Value(1)), default=0),
                has_related=Case(When(related__isnull=False, then=Value(1)), default=0),
                has_price=Case(
                    When((Q(price__isnull=False) & Q(price__gt=0)), then=Value(1)),
                    default=0,
                ),
            ).aggregate(
                descr500_cnt=Sum('descr500'),
                hasdescr_cnt=Sum('has_descr'),
                has_img_cnt=Sum('has_img'),
                has_img3_cnt=Sum('has_img3'),
                has_params_cnt=Sum('has_params'),
                has_props_cnt=Sum('has_props'),
                has_related_cnt=Sum('has_related'),
                has_price_cnt=Sum('has_price'),
            )
        else:
            qs = {}

        output = {
            'count': count,
            'has_description': qs.get('hasdescr_cnt', 0),
            'description_500': qs.get('descr500_cnt', 0),
            'has_images': qs.get('has_img_cnt', 0),
            'min_3_img': qs.get('has_img3_cnt', 0),
            'has_params': qs.get('has_params_cnt', 0),
            'has_props': qs.get('has_props_cnt', 0),
            'has_related': qs.get('has_related_cnt', 0),
            'max_img_size': self.get_max_product_img_size(
                category_id, published_product_status=published
            ),
            'has_price': qs.get('has_price_cnt', 0),
        }
        return output

    def get_category_meta_title(self, category: Category) -> str:
        try:
            seo_meta = MetaTag.objects.get(url=category.get_absolute_url())
        except MetaTag.DoesNotExist:
            pass
        else:
            return seo_meta.title

        title = category.name
        if config.SEO_CATEGORY_META_TITLE_PREFIX:
            title = f'{config.SEO_CATEGORY_META_TITLE_PREFIX} {title}'
        if config.SEO_CATEGORY_META_TITLE_SUFFIX:
            title = f'{title} {config.SEO_CATEGORY_META_TITLE_SUFFIX}'
        return title

    def get_category_h1(self, category: Category) -> str:
        try:
            seo_meta = MetaTag.objects.get(url=category.get_absolute_url())
            return seo_meta.h1
        except MetaTag.DoesNotExist:
            pass
        h1 = category.name
        if config.SEO_CATEGORY_META_H1_PREFIX:
            h1 = f'{config.SEO_CATEGORY_META_H1_PREFIX} {h1}'
        if config.SEO_CATEGORY_META_H1_SUFFIX:
            h1 = f'{h1} {config.SEO_CATEGORY_META_H1_SUFFIX}'

        return h1

    @cached_property
    def categories_report_published(self) -> dict[str, Any]:
        return self.categories_report_summary(published=True)

    @cached_property
    def categories_report_unpublished(self) -> dict[str, Any]:
        return self.categories_report_summary(published=False)

    def categories_report_summary(
        self, published: Optional[bool] = None
    ) -> dict[str, Any]:
        """
        - картинка категорий (есть/нет)
        - seo-текст категории (есть/нет)
        - топ-товары категории (есть/нет)
        - связанные категории (есть/нет)
        - сформированные h1 и title (только когда раскрыт список)
        """
        if published is None:
            qs = Category.objects.all()
        else:
            qs = Category.objects.filter(published=published)

        items = []

        summary = {
            'count': qs.count(),
            'has_image': 0,
            'has_seo_text': 0,
            'has_related': 0,
            'has_top_products': 0,
        }

        for cat in qs:
            if cat.image:
                summary['has_image'] += 1
            has_seo_text = cat.has_seo_text
            if has_seo_text:
                summary['has_seo_text'] += 1

            related = cat.related_categories.exists()
            if related:
                summary['has_related'] += 1
            if cat.products.filter(is_hit=True).exists():
                summary['has_top_products'] += 1

            items.append(
                {
                    'name': cat.name,
                    'has_image': bool(cat.image),
                    'has_seo_text': has_seo_text,
                    'has_related': related,
                    'params_count': cat.categoryparametermembership_set.count(),
                    'meta_title': self.get_category_meta_title(cat),
                    'h1': self.get_category_h1(cat),
                    # 'has_top_products': False,
                    # 'has_meta': False,
                }
            )
        data = {'items': items, 'summary': summary}
        return data

    @cached_property
    def check_telebot(self) -> bool:
        output = bool(
            telebot_is_active()
            and (
                (config.TELEBOT_CHAT_ID not in (0, -1001703147443))
                or config.TELEBOT_CHAT_IDS
            )
        )
        return output

    @cached_property
    def check_yandex_metrika(self) -> bool:
        """
        яндекс метрика (есть/нет, нужно парсить наличие счетчика, не просто факт заполнения поля в настройках)
        """
        return config.YANDEX_METRIKA_CODE and self.parser.check_yandex_metrika()

    @cached_property
    def check_robots_txt(self) -> bool:
        """
        robots.txt (есть/нет)
        """
        try:
            return apps.get_model('seo.RobotsTxt').objects.exists()
        except Exception:
            return False

    @cached_property
    def check_contact_minimum(self) -> bool:
        """
        минимум 1 запись в “контактах” (есть/нет)
        """
        try:
            return apps.get_model('addresses.Contact').objects.count() > 0
        except Exception:
            return False

    @cached_property
    def news_actions_count(self) -> int:
        """
        кол-во новостей/акций
        """
        try:
            return apps.get_model('news.News').objects.filter(published=True).count()
        except Exception:
            return 0

    @cached_property
    def sites_check(self) -> bool:
        """
        Проверка правильности настройки "сайтов" (/admin/sites/site/).
        Детали актуальной логики сего смотреть в задаче.
        https://redmine.nastroyker.ru/issues/17626
        """
        Site = apps.get_model('sites.Site')
        try:
            site = Site.objects.get(id=1)
        except Site.DoesNotExist:
            return False

        settings_domain = getattr(settings, 'BASE_URL', '').rsplit('//')[-1]
        return bool(site.domain == settings_domain)

    @cached_property
    def staticpage_count(self) -> int:
        """
        кол-во статичных страниц
        """
        try:
            return (
                apps.get_model('staticpages.Page').objects.count()
                + apps.get_model('staticpages.PageContructor').objects.count()
            )
        except Exception:
            return 0

    @cached_property
    def frontpage_h1(self) -> Optional[str]:
        """
        главная - h1
        """
        if data := self.parsed_data.get('h1'):
            return data[0]

    @cached_property
    def frontpage_h2(self) -> Optional[str]:
        """
        главная - h2
        """
        if data := self.parsed_data.get('h2'):
            return data

    @cached_property
    def frontpage_title(self) -> Optional[str]:
        """
        главная - title
        """
        if data := self.parsed_data.get('title'):
            return data[0]

    @cached_property
    def frontpage_description(self) -> Optional[str]:
        """
        главная - description
        """
        if data := self.parsed_data.get('description'):
            return data[0]

    @cached_property
    def frontpage_keywords(self) -> Optional[str]:
        """
        главная - keywords
        """
        if data := self.parsed_data.get('keywords'):
            return data[0]

    @cached_property
    def products_published_stats(self) -> dict[str, Any]:
        return self.get_products_summary(published=True)

    @cached_property
    def products_unpublished_stats(self) -> dict[str, Any]:
        return self.get_products_summary(published=False)

    @cached_property
    def calculate_common_settings_points(self) -> int:
        """
        https://redmine.nastroyker.ru/issues/16500
        общие настройки, тут 10 составляющих:
            все составляющие - есть/нет
            т.е. сколько пунктов есть, такая и оценка
            в нашем кейсе 100% = 10

        upd
            + https://redmine.nastroyker.ru/issues/17626
        """
        output = 0

        #  https://redmine.nastroyker.ru/issues/17626
        if self.sites_check:

            for i in (
                self.frontpage_h1,
                self.frontpage_title,
                self.frontpage_description,
                self.frontpage_keywords,
                config.MANAGER_EMAILS,
                self.check_contact_minimum,
                config.FAVICON_FILE,
                self.check_robots_txt,
                self.check_yandex_metrika,
                self.check_telebot,
            ):
                if bool(i):
                    output += 1
        return output

    @cached_property
    def calculate_categories_points(self) -> int | float:
        """
        https://redmine.nastroyker.ru/issues/16500

        сначала высчитываем процент наличия:
        - картинки (85/86 = 99%) - значимость 0.2
        - сео-текста (70/86 = 81%) - значимость 0.6
        - топ-товаров (51/86 = 59%) - значимость 0.1
        - связанных категорий (65/86 = 76%) - значимость 0.1
        дальше взвешиваем в зависимости от значимости
        99*0.2 + 81*0.6 + 59*0.1 + 76*0.1 = 82% = 8.2
        """
        output = 0

        # https://redmine.nastroyker.ru/issues/18678
        summary_dict = self.categories_report_published
        data = summary_dict.get('summary') or {}

        one_percent_value = (data.get('count') or 0) / 100

        # - картинки (85/86 = 99%) - значимость 0.2
        output += (
            round(data['has_image'] / one_percent_value)
            * self.CATEGORIES_POINT_HAS_IMAGE_COEFF
        )

        # - сео-текста (70/86 = 81%) - значимость 0.6
        output += (
            round(data['has_seo_text'] / one_percent_value)
            * self.CATEGORIES_POINT_HAS_SEOTEXT_COEFF
        )

        # - топ-товаров (51/86 = 59%) - значимость 0.1
        output += (
            round(data['has_top_products'] / one_percent_value)
            * self.CATEGORIES_POINT_HAS_TOP_PROD_COEFF
        )

        # - связанных категорий (65/86 = 76%) - значимость 0.1
        output += (
            round(data['has_related'] / one_percent_value)
            * self.CATEGORIES_POINT_HAS_RELATED_COEFF
        )

        return round(output / 10, 1)

    def _image_size_is_allowed(self, img_size: int, img_size_uom: str) -> bool:
        max_size: int | float = self.MAX_ALLOWED_IMG_SIZE_MB
        if img_size_uom == self.EXT_KB:
            max_size *= 1024
        elif img_size_uom == self.EXT_GB:
            max_size /= 1024
        return bool(img_size <= max_size)

    @cached_property
    def calculate_product_points(self) -> int | float:
        """
        https://redmine.nastroyker.ru/issues/16500

        опубликованные товары
        высчитываем процент наличия и взвешиваем:

        Min одна картинка (вес 0.3) = 2134/2138 = 99%
        Min три картинки (вес 0.05) = 1334/2138 = 62%

        # Описание (вес 0.2) = = 1997/2138 = 93%
        # Описание от 500 символов (вес 0.05) = = 455/2138 = 21%

        Описание (вес 0.25) = = 1997/2138 = 93%
        Параметры ИЛИ Свойства, берем максимальное из двух и высчитываем его (вес 0.3) = 1691/2138 = 79%
        Сопутствующие товары (вес 0.1) = 156/2138 = 7%

        Max вес изображений - если есть картинка более 1мб,
            то уменьшает оценку блока на 2 (в нашем кейсе тяжелых картинок нет)
        99*0.3 + 62*0.05 + 93*0.2 + 21*0.05 + 79*0.3 + 7*0.1 = 77% = 7.7

        последние вводные: https://redmine.nastroyker.ru/issues/18678
        """

        output = 0
        data = self.products_published_stats

        one_percent_value = (data.get('count') or 0) / 100

        # Min одна картинка (вес 0.3) = 2134/2138 = 99%
        output += (
            round(data['has_images'] / one_percent_value)
            * self.PRODUCTS_POINT_HAS_IMG_COEFF
        )

        # Min три картинки (вес 0.05) = 1334/2138 = 62%
        output += (
            round(data['min_3_img'] / one_percent_value)
            * self.PRODUCTS_POINT_MIN_3_IMG_COEFF
        )

        # Параметры ИЛИ Свойства, берем максимальное из двух и высчитываем его (вес 0.3) = 1691/2138 = 79%
        params_or_props = max(data['has_params'], data['has_props'])
        output += (
            round(params_or_props / one_percent_value)
            * self.PRODUCTS_POINT_HAS_PARAMS_COEFF
        )

        # Сопутствующие товары (вес 0.1) = 156/2138 = 7%
        output += (
            round(data['has_related'] / one_percent_value)
            * self.PRODUCTS_POINT_HAS_RELATED_COEFF
        )
        output = round(output / 10, 1)

        # Max вес изображений - если есть картинка более 1мб,
        #     то уменьшает оценку блока на 2
        if not self._image_size_is_allowed(
            data['max_img_size'][0], data['max_img_size'][1]
        ):
            output -= self.PRODUCTS_BIG_IMG_MINUS_VALUE

        return output

    def calculate_summary_point(self) -> int | float:
        result = (
            sum(
                (
                    self.calculate_common_settings_points,
                    self.calculate_categories_points,
                    self.calculate_product_points,
                )
            )
            / 3
        )
        return round(result, 1)

    def get_frontpage_ai_keywords(self) -> str:
        try:
            seo_meta = MetaTag.objects.get(url='/')
        except MetaTag.DoesNotExist:
            pass
        else:
            return seo_meta.ai_keywords
        return ''
