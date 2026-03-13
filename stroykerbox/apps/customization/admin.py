from django.contrib import admin
from django import forms
from django.forms.models import BaseInlineFormSet
from django.utils.translation import ugettext, ugettext_lazy as _
from constance import config
from mptt.admin import DraggableMPTTAdmin
from stroykerbox.apps.customization import DEFAULT_TAG_CONTAINERS
from stroykerbox.apps.utils.constance_helpers import get_config_list

from .models import (SliderTagContainer, SliderTagContainerItem, ColorScheme,
                     CustomFont, CustomStyle, CustomScript, CustomTemplateBlock, MobileMenuButton)
from .helpers import get_new_design_template_tags_list


# Контейнеры нового дизайна: в выпадающем списке тегов показываем только теги из get_new_design_template_tags_list().
NEW_DESIGN_CONTAINER_KEYS = ('new_design_middle', 'new_design_bottom', 'new_design_footer')


class ReadOnlyImageWidget(forms.Widget):
    """Виджет, который не рендерит input — только пустая ячейка (превью только из JS)."""

    def render(self, name, value, attrs=None, renderer=None):
        return ''


class SliderTagContainerItemForm(forms.ModelForm):
    class Meta:
        model = SliderTagContainerItem
        fields = '__all__'

    def __init__(self, *args, container=None, **kwargs):
        if 'container' in kwargs:
            container = kwargs.pop('container')
        super().__init__(*args, **kwargs)
        if container and getattr(container, 'key', None) in NEW_DESIGN_CONTAINER_KEYS:
            container_key = getattr(container, 'key', None)
            choices = get_new_design_template_tags_list(container_key)
            # Чтобы уже сохранённый тег (если его убрали из списка) отображался и сохранялся
            if self.instance and getattr(self.instance, 'tag_line', None):
                tag_line = self.instance.tag_line
                if not any(c[0] == tag_line for c in choices):
                    choices = [(tag_line, tag_line)] + list(choices)
            self.fields['tag_line'].choices = choices
            # Превью только из ND_TAG_PREVIEWS в JS — скрываем виджет загрузки
            if 'preview_image' in self.fields:
                self.fields['preview_image'].widget = ReadOnlyImageWidget()
                self.fields['preview_image'].required = False


class SliderTagContainerItemFormSet(BaseInlineFormSet):
    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs = dict(kwargs) if kwargs else {}
        kwargs['container'] = self.instance
        return kwargs


class SliderTagContainerItemInline(admin.TabularInline):
    model = SliderTagContainerItem
    form = SliderTagContainerItemForm
    formset = SliderTagContainerItemFormSet
    extra = 0

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if obj and getattr(obj, 'key', None) in NEW_DESIGN_CONTAINER_KEYS:
            fields = [f for f in fields if f != 'preview_image']
        return fields

    def get_formset(self, request, obj=None, **kwargs):
        """
        На контейнерах нового дизайна ограничиваем выпадающий список tag_line только new_design-тегами.
        Явно передаём fields без preview_image (без вызова get_fields, чтобы не было рекурсии).
        """
        if obj and getattr(obj, 'key', None) in NEW_DESIGN_CONTAINER_KEYS:
            model = self.model
            all_names = [f.name for f in model._meta.fields]
            kwargs['fields'] = [n for n in all_names if n != 'preview_image']
        formset = super().get_formset(request, obj, **kwargs)
        if obj and getattr(obj, 'key', None) in NEW_DESIGN_CONTAINER_KEYS:
            formset.form.base_fields['tag_line'].choices = get_new_design_template_tags_list(
                getattr(obj, 'key', None)
            )
        return formset


@admin.register(SliderTagContainer)
class SliderTagContainerAdmin(admin.ModelAdmin):
    inlines = (SliderTagContainerItemInline,)
    list_display = ('name', 'key')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        curr_containers = set(get_config_list('DISPLAY_TAG_CONTAINERS'))

        excluded_keys = set(DEFAULT_TAG_CONTAINERS.keys()) - curr_containers

        return qs.exclude(key__in=excluded_keys)

    def get_prepopulated_fields(self, request, obj=None):
        if not hasattr(obj, 'key'):
            return {'key': ('name',)}
        return super().get_prepopulated_fields(request, obj)


@admin.register(ColorScheme)
class ColorSchemeAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')

    fieldsets = (
        (None, {
            'fields': ('name', 'active', 'category_preview_height',
                       ),
        }),
        (_('Основые цвета'), {
            'classes': ('collapse',),
            'fields': ('main_elements_color', 'main_elements_hover_color'),
        }),
        (_('Кнопки: Основной набор (primary)'), {
            'classes': ('collapse',),
            'fields': [f.name for f in ColorScheme._meta.fields if f.name.startswith('color_button_primary')],
            'description': '<br />'.join([
                ugettext('- форма подарка'),
                ugettext('- форма в подвале и подписка в подвале'),
                ugettext('- кнопки "далее" и "отправить" в корзине'),
                ugettext('- кнопки сохранения в ЛК в анкете'),
                ugettext('- кнопка применения фильтров'),
                ugettext('- кнопка "отправить" в попапе запроса звонка'),
                ugettext('- кнопка заказа звонка в мобильном меню')
            ])
        }),
        (_('Кнопки: Основной набор (secondary)'), {
            'classes': ('collapse',),
            'fields': [f.name for f in ColorScheme._meta.fields if f.name.startswith('color_button_secondary')],
            'description': '<br />'.join([
                ugettext('- кнопка на превью товара 2.0/1, когда товар без цены'),
                ugettext('- кнопка на превью товара 1.0, когда нет цены или наличия'),
                ugettext('- кновка выхода из ЛК'),
                ugettext('- кнопка "подробнее" на первом превью акций'),
                ugettext('- кнопка добавления к сравнению на превью товара 1.0'),
                ugettext('- кнопка "заказать доставку" в карточке товара в сайдбаре')
            ])
        }),
        (_('Кнопки: Основной набор (muted)'), {
            'classes': ('collapse',),
            'fields': [f.name for f in ColorScheme._meta.fields if f.name.startswith('color_button_muted')],
            'description': _('- кнопка на превью товара 2.0/1, когда товара нет в наличии')
        }),
        (_('Кнопки: Основной набор (callme)'), {
            'classes': ('collapse',),
            'fields': [f.name for f in ColorScheme._meta.fields if f.name.startswith('color_button_callme')],
            'description': _('- кнопка запроса звонка в шапке')
        }),
        (_('Кнопки: Запрос обр. звонка (старый вариант)'), {
            'classes': ('collapse',),
            'fields': ('callme_button_hover_color', 'callme_button_fill_color',
                       'callme_button_color', 'callme_button_fill_hover_color'),
        }),
        (_('Кнопки: Основной набор (cart)'), {
            'classes': ('collapse',),
            'fields': [f.name for f in ColorScheme._meta.fields if f.name.startswith('color_button_cart')],
            'description': '<br />'.join([
                ugettext('- корзина в версиях 2.0 и 2.1'),
                ugettext('- корзина в верчии 1.0'),
                ugettext('- корзина в карточке товара')
            ])
        }),
        (_('Кнопки: Корзина'), {
            'classes': ('collapse',),
            'fields': ['checkout_button_font_color'],
        }),
        (_('Кнопки: Цветные (общее)'), {
            'classes': ('collapse',),
            'fields': ('colorless_buttons_border_color', 'colorless_buttons_font_color',
                       'colorless_buttons_hover_bg'),
        }),
        (_('Кнопки: Плавающие'), {
            'classes': ('collapse',),
            'fields': ('color_fixedbtn', 'color_bg_fixedbtn'),
        }),
        (_('Кнопки: Счет'), {
            'classes': ('collapse',),
            'fields': ('invoice_button_color',
                       'invoice_button_font_color'),
        }),
        (_('Кнопки: Шапка'), {
            'classes': ('collapse',),
            'fields': ('header_buttons_font_color',),
        }),
        (_('Шапка'), {
            'classes': ('collapse',),
            'fields': ('category_menu_font_highlight_color', 'category_menu_underline_highlight_color',
                       'header_top_icon_color', 'header_top_bg_color', 'header_top_menu_font_color',
                       'header_top_menu_font_hover_color', 'header_top_phone_font_color',
                       'header_bg_color'),
        }),
        (_('Подвал'), {
            'classes': ('collapse',),
            'fields': ('footer_bg_color', 'footer_links',
                       'footer_links_hover', 'footer_title'),
        }),
        (_('Кастомный шрифт'), {
            'classes': ('collapse',),
            'fields': ('custom_font', 'custom_font_elements'),
        }),
        (_('Крошки'), {
            'classes': ('collapse',),
            'fields': ('breadcrumb_item_color', 'breadcrumb_item_hover_color',
                       'breadcrumb_sep_color'),
        }),
        (_('Форма поиска'), {
            'classes': ('collapse',),
            'fields': ('search_field_bg_color', 'search_field_border_color', 'search_field_btn_color',
                       'search_field_font_color', 'search_field_placeholder_font_color'),
        }),
        (_('Форма обратной связи'), {
            'classes': ('collapse',),
            'fields': ('feedback_form_section_bg_color', 'feedback_form_bg', 'feedback_form_title',
                       'feedback_form_text', 'feedback_form_border', 'feedback_form_input_border'),
        }),
        (_('Меню каталога'), {
            'classes': ('collapse',),
            'fields': ('catalog_menu_button_bg', 'color_main_dropdown_menu_bg', 'color_main_dropdown_menu_text',
                       'catalog_menu_bg_color', 'catalog_menu_hover_bg_color',
                       'catalog_menu_burger_color', 'catalog_menu_border_color',
                       'catalog_menu_font_color', 'catalog_menu_font_hover_color',
                       'catalog_menu_arrow_color', 'catalog_menu_link_hover'),
        }),
        (_('Товары'), {
            'classes': ('collapse',),
            'fields': ('hit_tag_bg_color', 'hit_tag_font_color', 'sale_tag_bg_color',
                       'sale_tag_font_color', 'discount_tag_bg_color', 'discount_tag_font_color',
                       'new_tag_bg_color', 'new_tag_font_color', 'product_preview_bg_color',
                       'color_card_border', 'product_preview_border_hover_color', 'product_list_header_link_color',
                       'product_list_header_link_hover_color', 'product_tab_link_color',
                       'product_tab_link_hover_color', 'color_product_online_price'),
        }),
        (_('Новости/Акции'), {
            'classes': ('collapse',),
            'fields': ('news_label_bg_color', 'news_label_font_color', 'action_label_bg_color',
                       'action_label_font_color'),
        }),
        (_('Статьи'), {
            'classes': ('collapse',),
            'fields': ('article_label_bg_color', 'article_label_font_color'),
        }),
        (_('Статичные страницы'), {
            'classes': ('collapse',),
            'fields': ('staticpage_box_fill_color', 'staticpage_box_border_color'),
        }),
        (_('Пользователи'), {
            'classes': ('collapse',),
            'fields': ('color_lk_accent_items', 'color_lk_items_bg',
                       'color_lk_items_border', 'color_lk_items_hover_bg'),
        }),
        (_('Разное'), {
            'classes': ('collapse',),
            'fields': ('frontpage_first_screen_bg_color', 'preview_font_color',
                       'preview_bg_color', 'preview_bg_hover_color', 'inner_page_bg'),
        }),
    )


@admin.register(CustomFont)
class CustomFontAdmin(admin.ModelAdmin):
    pass


class CustomStaticFile(admin.ModelAdmin):
    list_display = ('name', 'active', 'position')
    list_editable = ('position', 'active')

    def name(self, obj):
        if hasattr(obj, 'name'):
            return obj.name
        return ''


@admin.register(CustomStyle)
class CustomStyleAdmin(CustomStaticFile):
    pass


@admin.register(CustomScript)
class CustomSriptAdmin(CustomStaticFile):
    pass


@admin.register(CustomTemplateBlock)
class CustomTemplateBlockAdmin(admin.ModelAdmin):
    list_display = ('name', 'key')

    def get_prepopulated_fields(self, request, obj=None):
        if not hasattr(obj, 'key'):
            return {'key': ('name',)}
        return super().get_prepopulated_fields(request, obj)


@admin.register(MobileMenuButton)
class MobileMenuButtonAdmin(DraggableMPTTAdmin):
    list_display = ('tree_actions', 'indented_title',
                    'get_type_display', 'active',)
    list_display_links = ('indented_title',)
