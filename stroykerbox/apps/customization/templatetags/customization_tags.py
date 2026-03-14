import uuid
import logging

from django import template
from django.core.cache import cache
from django.apps import apps
from constance import config

from stroykerbox.apps.customization.models import SliderTagContainer
from stroykerbox.apps.menu.models import Menu
from stroykerbox.apps.commerce.cart import Cart


logger = logging.getLogger(__name__)


register = template.Library()


def get_tag_classes(tag, tag_args=None):
    tag_classes = tag.replace('render_', '')
    if tag_classes == 'statictext' and tag_args:
        tag_classes += f' {tag_args[0].strip()} text-page'
    elif tag_classes == 'big_banners':
        # BB hack
        if config.BB_DISPLAY_MODE == 'extrawide':
            tag_classes += ' wide-container'
        elif config.BB_DISPLAY_MODE == 'sidebar':
            tag_classes += ' py--2'
    return tag_classes


def get_html_for_container_tag(context, container):
    html = []
    sliders = container.sliders.filter(enabled=True)
    path = (context.get('request') or {}).path or ''
    # По умолчанию: frontpage_only=True показываем на главной (/) и на тестовой /8march_design/
    # Для футера: frontpage_only=True только на главной (/), чтобы на тестовой не дублировалось.
    if container.key == 'new_design_footer':
        if path != '/':
            sliders = sliders.filter(frontpage_only=False)
    elif path != '/' and not path.startswith('/8march_design'):
        sliders = sliders.filter(frontpage_only=False)

    for slider in sliders:
        module, tag = slider.tag_line.split(':')
        load_tag_line = f'{{% load {module} %}}'
        slider_args = slider.args.split(',') if slider.args else None

        if slider_args:
            cleanded_args = ' '.join([f'"{a.strip()}"' for a in slider_args])
            code_line = f'{{% {tag} {cleanded_args} %}}'
        else:
            code_line = f'{{% {tag} %}}'

        try:
            context.update(
                {
                    'custom_block_title': slider.block_title,
                    'custom_block_title_color': slider.title_color,
                }
            )
            code = template.Template(load_tag_line + code_line).render(context)
        except Exception as e:
            logger.exception(
                'Tag container item failed: container=%s tag_line=%s: %s',
                container.key, slider.tag_line, e
            )
            pass
        else:
            if not code.strip():
                continue

            html.append(
                {
                    'without_wrapper': slider.without_wrapper,
                    'wrapper_classes': slider.wrapper_classes,
                    'tag_class': get_tag_classes(tag, slider_args),
                    'bg_color': slider.bg_color,
                    'bg_image_url': slider.bg_image.url if slider.bg_image else None,
                    'top_indent': slider.top_indent,
                    'bottom_indent': slider.bottom_indent,
                    'code': code,
                }
            )
    return html


@register.inclusion_tag('customization/tags/tag-container.html', takes_context=True)
def render_tag_container(context, key=None, wrapper_main_class='conditional-section'):
    try:
        container = SliderTagContainer.objects.prefetch_related('sliders').get(key=key)
    except SliderTagContainer.DoesNotExist:
        return
    if container.cache:
        html = cache.get_or_set(
            container.cache_key,
            get_html_for_container_tag(context, container),
            container.cache_timeout,
        )
    else:
        html = get_html_for_container_tag(context, container)

    context['html'] = html
    context['wrapper_main_class'] = wrapper_main_class
    return context


@register.simple_tag()
def custom_colors_is_active():
    """
    Check that custom colors are used.
    """
    from stroykerbox.apps.customization.models import ColorScheme

    return ColorScheme.objects.filter(active=True).exists()


@register.filter
def to_css_var(python_var, starts):
    if isinstance(python_var, str):
        return f'--{python_var.replace("_", "-")}'
    return python_var


@register.simple_tag()
def render_main_buttons_css_vars(scheme):
    fields = []
    for f in scheme._meta.fields:
        if f.name.startswith('color_button'):
            value = getattr(scheme, f.name, '')
            if value:
                fields.append(f'--{f.name.replace("_", "-")}: {value};')
    return '\n'.join(fields)


@register.simple_tag()
def custom_colors_css_version():
    from stroykerbox.apps.customization.models import ColorScheme

    return cache.get_or_set(ColorScheme.VERSION_CACHE_KEY, uuid.uuid4().hex[:8], None)


@register.inclusion_tag('customization/tags/custom-styles.html')
def render_custom_styles():
    CustomStyle = apps.get_model('customization.CustomStyle')
    if not CustomStyle:
        return {}
    styles = CustomStyle.objects.filter(active=True)
    context = {'custom_styles': styles}
    context['has_inline'] = (
        styles.filter(inline_styles__isnull=False).exclude(inline_styles='').exists()
    )
    context['has_files'] = styles.filter(file__isnull=False).exists()
    return context


@register.inclusion_tag('customization/tags/custom-scripts.html')
def render_custom_scripts():
    CustomScript = apps.get_model('customization.CustomScript')
    if not CustomScript:
        return {}
    scripts = CustomScript.objects.filter(active=True)
    context = {'custom_scripts': scripts}
    context['has_inline'] = (
        scripts.filter(inline_scripts__isnull=False).exclude(inline_scripts='').exists()
    )
    context['has_files'] = scripts.filter(file__isnull=False).exists()
    return context


@register.inclusion_tag(
    'customization/tags/custom-template-block.html', takes_context=True
)
def render_custom_template_block(context, key):
    from stroykerbox.apps.customization.models import CustomTemplateBlock

    try:
        block = CustomTemplateBlock.objects.get(key=key)
    except CustomTemplateBlock.DoesNotExist:
        return

    code = template.Template(block.code).render(context)
    context['template_code'] = code
    return context


@register.inclusion_tag('custom_headers/header-base.html', takes_context=True)
def render_header(context, **kwargs):
    header_menu_key = kwargs.get('header_menu_key', 'header_menu')
    header_menu_limit = kwargs.get('header_menu_limit', None)

    try:
        menu = Menu.objects.get(key=header_menu_key)
        context['header_menu'] = menu.get_published_items[:header_menu_limit]
    except Menu.DoesNotExist:
        context['header_menu'] = []

    context['cart'] = context.get('cart', Cart.from_request(context['request']))

    # Fallback при пустом CUSTOM_HEADER_ID (локальная среда / дамп без значения). У заказчика значение задано — без изменений.
    context['current_header_template'] = (
        f'custom_headers/header-{config.CUSTOM_HEADER_ID or "0"}.html'
    )
    return context


@register.inclusion_tag('custom_headers/header-mobile-base.html', takes_context=True)
def render_mobile_header(context, **kwargs):
    context['cart'] = context.get('cart', Cart.from_request(context['request']))

    # Fallback при пустом CUSTOM_MOBILE_HEADER_ID — см. комментарий в render_header.
    context['current_mobile_header_template'] = (
        f'custom_headers/header-mobile-{config.CUSTOM_MOBILE_HEADER_ID or "1"}.html'
    )
    return context


@register.inclusion_tag('custom_headers/logo-image.html', takes_context=True)
def render_logo_image(context, mobile=False):
    context['mobile_mode'] = mobile
    return context


@register.inclusion_tag('customization/tags/new_design_info_block.html', takes_context=True)
def render_new_design_info_block(context):
    """new_design: гарантия качества / доставка / подарки + рейтинги 2ГИС и Яндекс."""
    return context


@register.inclusion_tag('customization/tags/new_design_social_block.html', takes_context=True)
def render_new_design_social_block(context):
    """new_design: соцсети (Telegram, VK)."""
    return context


@register.inclusion_tag('customization/tags/new_design_reviews_block.html', takes_context=True)
def render_new_design_reviews_block(context):
    """new_design: отзывы."""
    return context


@register.inclusion_tag('customization/tags/new_design_map_block.html', takes_context=True)
def render_new_design_map_block(context):
    """new_design: карта / контакты."""
    return context


@register.inclusion_tag('customization/tags/new_design_footer_questions_block.html', takes_context=True)
def render_new_design_footer_questions_block(context):
    """new_design: футер — «Остались вопросы?» (форма, телефон, Перезвоните мне)."""
    return context


@register.inclusion_tag('customization/tags/new_design_footer_menu_block.html', takes_context=True)
def render_new_design_footer_menu_block(context):
    """new_design: футер — колонки «Каталог» и «Покупателям». """
    return context


@register.inclusion_tag('customization/tags/new_design_footer_copyright_block.html', takes_context=True)
def render_new_design_footer_copyright_block(context):
    """new_design: футер — копирайт © «LUCIANO», YYYY."""
    return context


@register.inclusion_tag('customization/tags/new_design_bouquets_block.html', takes_context=True)
def render_new_design_bouquets_block(context):
    """new_design: сборные букеты."""
    return context


@register.inclusion_tag('customization/tags/new_design_bouquet_wish_block.html', takes_context=True)
def render_new_design_bouquet_wish_block(context):
    """new_design: букет по вашим желаниям (форма). Контекст из тегов не содержит форму — добавляем здесь (как во view_8march_design_test и в crm_tags)."""
    from stroykerbox.apps.crm.forms import FeedbackMessageForm
    context['feedback_form'] = FeedbackMessageForm()
    return context


@register.inclusion_tag('customization/tags/new_design_collection_block.html', takes_context=True)
def render_new_design_collection_block(context):
    """new_design: коллекция (карусель)."""
    return context


@register.inclusion_tag('customization/tags/new_design_categories_block.html', takes_context=True)
def render_new_design_categories_block(context):
    """new_design: рубрики (овальные картинки)."""
    return context


@register.inclusion_tag('customization/tags/new_design_hero_block.html', takes_context=True)
def render_new_design_hero_block(context):
    """new_design: герой (верхняя карусель)."""
    return context


@register.inclusion_tag(
    'catalog/tags/new_spring_design_sale-products-slider.html', takes_context=True
)
def render_new_design_actions_block(context, limit=12):
    """
    new_design: АКЦИИ.

    Логика отбора сохранена по блоку в view_8march_design_test:
    - published=True
    - сначала is_action=True
    - если пусто -> categories__slug='8-marta'
    - если пусто -> просто published=True
    - обязательны обе цены (price + old_price) для текущей локации
    """
    try:
        Product = apps.get_model('catalog', 'Product')
    except Exception:
        return {}

    request = context.get('request')
    location = getattr(request, 'location', None) if request else None

    qs = (
        Product.objects.filter(published=True, is_action=True)
        .prefetch_related('images')
        .distinct()
    )
    if not qs.exists():
        qs = (
            Product.objects.filter(published=True, categories__slug='8-marta')
            .prefetch_related('images')
            .distinct()
        )
    if not qs.exists():
        qs = Product.objects.filter(published=True).prefetch_related('images').distinct()

    products = []
    for product in qs.order_by('-updated_at'):
        price_obj = product.location_price_object(location)
        main_price = (
            getattr(price_obj, 'currency_price', None)
            or getattr(price_obj, 'price', None)
            or getattr(product, 'currency_price', None)
            or getattr(product, 'price', None)
        )
        old_price = (
            getattr(price_obj, 'currency_old_price', None)
            or getattr(price_obj, 'old_price', None)
            or getattr(product, 'currency_old_price', None)
            or getattr(product, 'old_price', None)
        )
        if main_price in (None, '') or old_price in (None, ''):
            continue

        products.append(product)
        if len(products) >= int(limit or 12):
            break

    return {'products': products}
