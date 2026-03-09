from decimal import Decimal, InvalidOperation

from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, re_path, include
from django.conf.urls.static import static
from django.conf import settings
from django.views.decorators.cache import cache_page
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

from rest_framework.authtoken import views
from filebrowser.sites import site
from constance import config
from stroykerbox.apps.catalog.views import CatalogFrontpageView, yml_export
from stroykerbox.apps.seo.views import robots_txt
from stroykerbox.apps.catalog import sitemap as catalog_sitemap
from stroykerbox.apps.staticpages import sitemap as staticpages_sitemap
from stroykerbox.apps.articles import sitemap as articles_sitemap
from stroykerbox.apps.news import sitemap as news_sitemap
from stroykerbox.apps.addresses.views import ContactsPageView
from stroykerbox.apps.utils.views import clear_cache, clear_thumbnail_cache
from stroykerbox.apps.search.views import SearchResult
from stroykerbox.apps.common.views import StaffCheckPage, DashboardPage
from stroykerbox.apps.crm.forms import FeedbackMessageForm
from stroykerbox.apps.catalog.models import Product

YML_URL = getattr(config, 'YML_URL', 'catalog_export.yml') or 'catalog_export.yml'


def view_8march_design_test(request):
    """Тестовая страница 8march: главная + хэдер + футер. Контекст для includes/header_8march_standalone и footer_8march_standalone."""
    cart = (request.session.get('cart') or []) if hasattr(request, 'session') else []
    cart_count = len(cart) if isinstance(cart, (list, tuple)) else 0
    header_logo_url = footer_logo_url = header_phone = footer_contacts = ''
    social_link_telegram = social_link_vk = ''
    try:
        media_url = getattr(settings, 'MEDIA_URL', '') or ''
        header_logo = getattr(config, 'HEDER_LOGO_FILE', None) or getattr(config, 'HEADER_LOGO_FILE', None)
        header_logo_url = (media_url + header_logo) if header_logo else ''
        footer_logo = getattr(config, 'FOOTER_LOGO_FILE', None)
        footer_logo_url = (media_url + footer_logo) if footer_logo else ''
        header_phone = getattr(config, 'CONTACT_PHONE', None) or getattr(config, 'PHONE', None) or ''
        footer_contacts = getattr(config, 'MAIL__FOOTER_CONTACTS', None) or ''
        social_link_telegram = getattr(config, 'SOCIAL_LINK_TELEGRAM', None) or ''
        social_link_vk = getattr(config, 'SOCIAL_LINK_VK', None) or ''
    except Exception:
        pass
    # Рубрика с овальными картинками: фиксированная логика как на lucianoflowers.ru.
    # ВАЖНО: соответствие "картинка/подпись -> slug" менять самостоятельно нельзя;
    # правки только по прямому согласованию с заказчиком.
    category_slots = (
        ('images/gotovaya-vitrina.png', 'Готовая витрина', 'ГОТОВАЯ<br>ВИТРИНА', 'gotovaya-vitrina'),
        ('images/monoduo-bukety.png', 'Моно букеты', 'МОНО<br>БУКЕТЫ', 'monoduo-bukety'),
        ('images/kompozicii.png', 'Композиции', 'КОМПОЗИЦИИ', 'kompozicii'),
        ('images/wow-effect.png', 'Эффектные букеты', 'ЭФФЕКТНЫЕ<br>БУКЕТЫ', 'wow-bukety'),
        ('images/fresh-buketi.png', 'Интерьерные букеты', 'ИНТЕРЬЕРНЫЕ<br>БУКЕТЫ', 'fresh-bukety'),
        ('images/podarki.png', 'Подарки', 'ПОДАРКИ', 'podarki'),
    )
    categories_8march = []
    for img, alt, label, slug in category_slots:
        try:
            url = reverse('catalog:category', kwargs={'category_slug': slug})
        except Exception:
            url = reverse('catalog:index')
        categories_8march.append({
            'url': url,
            'image': img,
            'alt': alt,
            'label': label,
        })

    def _format_price(value):
        if value in (None, ''):
            return ''
        try:
            amount = Decimal(value).quantize(Decimal('1'))
        except (InvalidOperation, TypeError, ValueError):
            return ''
        return f"{int(amount):,}".replace(',', ' ') + ' P'

    location = getattr(request, 'location', None)
    # АКЦИИ (ORIGINAL) — НЕ МЕНЯТЬ.
    # Раскомментировать только по прямой команде заказчика.
    # # ВАЖНО: условие отбора товаров в блок «АКЦИИ» (published + обязательны обе цены) не менять без прямого указания заказчика.
    # # promo_qs = Product.objects.filter(published=True, is_action=True).prefetch_related('images').distinct()
    # promo_qs = Product.objects.filter(published=True).prefetch_related('images').distinct()
    # if not promo_qs.exists():
    #     promo_qs = Product.objects.filter(published=True, categories__slug='8-marta').prefetch_related('images').distinct()
    # if not promo_qs.exists():
    #     promo_qs = Product.objects.filter(published=True).prefetch_related('images')
    #
    # promo_products = []
    # for product in promo_qs.order_by('-updated_at'):
    #     price_obj = product.location_price_object(location)
    #     main_price = (
    #         getattr(price_obj, 'currency_price', None)
    #         or getattr(price_obj, 'price', None)
    #         or product.currency_price
    #         or product.price
    #     )
    #     old_price = (
    #         getattr(price_obj, 'currency_old_price', None)
    #         or getattr(price_obj, 'old_price', None)
    #         or product.currency_old_price
    #         or product.old_price
    #     )
    #     main_price_fmt = _format_price(main_price)
    #     old_price_fmt = _format_price(old_price)
    #     if not (main_price_fmt and old_price_fmt):
    #         continue
    #     image_url = ''
    #     if product.main_image and getattr(product.main_image, 'image', None):
    #         try:
    #             image_url = product.main_image.image.url
    #         except Exception:
    #             image_url = ''
    #     if not image_url:
    #         image_url = '/static/images/empty-product.svg'
    #
    #     promo_products.append({
    #         'url': product.get_absolute_url() or reverse('catalog:index'),
    #         'image': image_url,
    #         'alt': product.name or 'Товар',
    #         'price': main_price_fmt,
    #         'old_price': old_price_fmt,
    #     })
    #     if len(promo_products) >= 24:
    #         break

    # АКЦИИ (ACTIVE DUPLICATE) — НЕ МЕНЯТЬ.
    # ВАЖНО: условие отбора товаров в блок «АКЦИИ» (published + обязательны обе цены) не менять без прямого указания заказчика.
    # promo_qs = Product.objects.filter(published=True, is_action=True).prefetch_related('images').distinct()
    promo_qs = Product.objects.filter(published=True, categories__slug='8-marta').prefetch_related('images').distinct()

    promo_products = []
    for product in promo_qs.order_by('-updated_at'):
        price_obj = product.location_price_object(location)
        main_price = (
            getattr(price_obj, 'currency_price', None)
            or getattr(price_obj, 'price', None)
            or product.currency_price
            or product.price
        )
        old_price = (
            getattr(price_obj, 'currency_old_price', None)
            or getattr(price_obj, 'old_price', None)
            or product.currency_old_price
            or product.old_price
        )
        main_price_fmt = _format_price(main_price)
        old_price_fmt = _format_price(old_price)
        image_url = ''
        if product.main_image and getattr(product.main_image, 'image', None):
            try:
                image_url = product.main_image.image.url
            except Exception:
                image_url = ''
        if not image_url:
            image_url = '/static/images/empty-product.svg'

        promo_products.append({
            'url': product.get_absolute_url() or reverse('catalog:index'),
            'image': image_url,
            'alt': product.name or 'Товар',
            'price': main_price_fmt,
            'old_price': old_price_fmt,
        })
        if len(promo_products) >= 24:
            break

    bouquets_qs = Product.objects.filter(published=True, images__isnull=False).prefetch_related('images').distinct()
    bouquet_base = list(bouquets_qs.order_by('?')[:9])
    if not bouquet_base:
        bouquet_base = list(Product.objects.filter(published=True).prefetch_related('images').order_by('-updated_at')[:9])

    bouquet_products = []
    if bouquet_base:
        while len(bouquet_products) < 9:
            for product in bouquet_base:
                price_obj = product.location_price_object(location)
                main_price = (
                    getattr(price_obj, 'currency_price', None)
                    or getattr(price_obj, 'price', None)
                    or product.currency_price
                    or product.price
                )
                image_url = ''
                if product.main_image and getattr(product.main_image, 'image', None):
                    try:
                        image_url = product.main_image.image.url
                    except Exception:
                        image_url = ''
                if not image_url:
                    image_url = '/static/images/empty-product.svg'

                bouquet_products.append({
                    'url': product.get_absolute_url() or reverse('catalog:index'),
                    'image': image_url,
                    'alt': product.name or 'Сборный букет',
                    'name': product.name or 'Сборный букет',
                    'price': _format_price(main_price),
                })
                if len(bouquet_products) >= 9:
                    break
    else:
        bouquet_products = [{
            'url': reverse('catalog:index'),
            'image': '/static/images/empty-product.svg',
            'alt': 'Сборный букет',
            'name': 'Сборный букет',
            'price': '',
        } for _ in range(9)]

    return render(request, '8march_design_test.html', {
        'cart_count': cart_count,
        'header_phone': header_phone or None,
        'header_logo_url': header_logo_url or None,
        'footer_phone': header_phone or None,
        'footer_contacts': footer_contacts or None,
        'footer_logo_url': footer_logo_url or None,
        'feedback_form': FeedbackMessageForm(),
        'categories_8march': categories_8march,
        'promo_products': promo_products,
        'bouquet_products': bouquet_products,
        'social_link_telegram': social_link_telegram,
        'social_link_vk': social_link_vk,
    })


sitemaps = {
    'news': news_sitemap.NewsSitemap,
    'article': articles_sitemap.ArticleSitemap,
    'category': catalog_sitemap.CategorySitemap,
    'category_filter': catalog_sitemap.CategoryFilterSitemap,
    'product': catalog_sitemap.ProductSitemap,
    'staticpage': staticpages_sitemap.PageSitemap,
}

admin.site.site_header = config.ADMIN_SITE_HEADER
admin.site.site_title = config.ADMIN_SITE_META_TITLE

urlpatterns = [
    re_path(r'^$', CatalogFrontpageView.as_view(), name='frontpage'),
    # Тестовая страница 8march: доступна только локально (DEBUG=True)
    # На проде намеренно отключена.
    *([path('8march_design/', view_8march_design_test, name='8march-design-test')] if getattr(settings, 'DEBUG', False) else []),
    # Главная в старом дизайне (как у заказчика). Когда задан FORCE_OLD_DESIGN_PATH='prod29' — на /prod29/ показывается старый вид; иначе /prod29/ = то же что /.
    # Раскомментировать для разработки, когда нужен старый дизайн на /prod29/
    path('prod29/', CatalogFrontpageView.as_view(), name='frontpage-prod'),
]
# На проде можно не задавать FORCE_OLD_DESIGN_PATH — тогда /prod29/ просто дублирует главную.
_prod_path = getattr(settings, 'FORCE_OLD_DESIGN_PATH', None)
if _prod_path:
    _segment = (_prod_path if isinstance(_prod_path, str) else str(_prod_path)).strip('/')
    if _segment and _segment != 'prod29':
        urlpatterns.append(path(_segment + '/', CatalogFrontpageView.as_view(), name='frontpage-prod-alt'))
urlpatterns += [
    path('i18n/', include('django.conf.urls.i18n')),
    path('robots.txt', robots_txt, name='robots_txt'),
    path('admin/clear-cache/', clear_cache, name='clear_cache'),
    path(
        'admin/clear-thumbnail-cache/',
        clear_thumbnail_cache,
        name='clear_thumbnail_cache',
    ),
    path('admin/filebrowser/', site.urls),
    path('admin/', admin.site.urls),
    path('chaining/', include('smart_selects.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('catalog/', include('stroykerbox.apps.catalog.urls', namespace='catalog')),
    path('cart/', include('stroykerbox.apps.commerce.cart_urls', namespace='cart')),
    path('news/', include('stroykerbox.apps.news.urls', namespace='news')),
    path('crm/', include('stroykerbox.apps.crm.urls', namespace='crm')),
    path('articles/', include('stroykerbox.apps.articles.urls', namespace='articles')),
    path('user/', include('stroykerbox.apps.users.urls', namespace='users')),
    path('account/', include('stroykerbox.apps.users.auth_urls')),
    path('bnrs/', include('stroykerbox.apps.banners.urls')),
    path('django-rq/', include('django_rq.urls')),
    path('api-auth/', include('rest_framework.urls')),
    path('api/v1/', include('stroykerbox.apps.api.urls')),
    path('api-token-auth/', views.obtain_auth_token),
    path(
        'sitemap.xml',
        cache_page(60 * 60 * 6)(sitemap),
        {'sitemaps': sitemaps},  # noqa
        name='django.contrib.sitemaps.views.sitemap',
    ),
    path(
        'subscription/',
        include('stroykerbox.apps.subscription.urls', namespace='subscription'),
    ),
    path('geoip/', include('django_geoip.urls')),
    path('location/', include('stroykerbox.apps.locations.urls')),
    path('addresses/', include('stroykerbox.apps.addresses.urls')),
    path('contacts/', ContactsPageView.as_view(), name='contacts-page'),
    path('reviews/', include('stroykerbox.apps.reviews.urls')),
    path('customization/', include('stroykerbox.apps.customization.urls')),
    path('custom_forms/', include('stroykerbox.apps.custom_forms.urls')),
    path('search', SearchResult.as_view(), name='search'),
    path(YML_URL, yml_export, name='yml_export'),
    path('faq/', include('stroykerbox.apps.faq.urls')),
    path('fp/', include('django_drf_filepond.urls')),
    path('content-check/', StaffCheckPage.as_view(), name='staff-check-page'),
    path('dash/', DashboardPage.as_view(), name='dashboard'),
]

if 'stroykerbox.apps.portfolio' in settings.INSTALLED_APPS:
    urlpatterns += [path('portfolio/', include('stroykerbox.apps.portfolio.urls'))]

if 'stroykerbox.apps.smartlombard' in settings.INSTALLED_APPS:
    from stroykerbox.apps.smartlombard.views import (
        online_payment as smartlombard_online_payment,
    )

    urlpatterns += [
        path(
            'online-oplata/',
            smartlombard_online_payment,
            name='smartlombard-online-payment',
        ),
        path(
            'smartlombard/tbank/', include('stroykerbox.apps.smartlombard.tbank.urls')
        ),
        path('smartlombard/', include('stroykerbox.apps.smartlombard.urls')),
    ]

if 'stroykerbox.apps.booking' in settings.INSTALLED_APPS:
    urlpatterns += [path('booking/', include('stroykerbox.apps.booking.urls'))]

if settings.DEBUG or settings.TESTING_MODE:
    try:
        import debug_toolbar
    except (ImportError, ModuleNotFoundError):
        pass
    else:
        urlpatterns = (
            [
                path('__debug__/', include(debug_toolbar.urls)),
            ]
            + urlpatterns
            + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
        )


# Static pages. This must always be the last URL rule!
urlpatterns += [
    path('', include('stroykerbox.apps.staticpages.urls', namespace='staticpages'))
]


def get_app_list(self, request, app_label=None):
    """
    Return a sorted list of all the installed apps that have been
    registered in this site.
    """
    app_dict = self._build_app_dict(request, app_label)
    ordering = getattr(settings, 'APPS_ORDER', {})

    app_list = sorted(
        app_dict.values(),
        key=lambda x: ordering.get(x['app_label'].lower(), f'z{x["name"]}'),
    )

    for app in app_list:
        app['models'].sort(key=lambda x: x['name'])

    return app_list


admin.AdminSite.get_app_list = get_app_list
