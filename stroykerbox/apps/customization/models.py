import os

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.text import Truncator
from mptt.models import MPTTModel, TreeForeignKey

from colorfield.fields import ColorField
from stroykerbox.apps.utils.validators import validate_svg_or_image

from .helpers import get_slider_template_tags_list
from .config import ALLOWED_FONT_EXTENSIONS_LIST


class SliderTagContainer(models.Model):
    """
    A container for a contents of template tags with slider from different apps.
    """
    key = models.SlugField(_('key'), max_length=70, primary_key=True)
    name = models.CharField(_('name'), max_length=128)
    cache = models.BooleanField(_('cache enabled'), default=False)
    cache_timeout = models.PositiveIntegerField(
        _('cache timeout, sec'), blank=True, null=True)

    class Meta:
        verbose_name = _('templatetag container')
        verbose_name_plural = _('templatetag containers')

    def __str__(self):
        return self.name

    @property
    def cache_key(self):
        return f'customization:slidertagcontainer:{self.key}'


class TagContainerItemAbstract(models.Model):
    tag_line = models.CharField(_('tag function name'),
                                choices=get_slider_template_tags_list(), max_length=60,
                                help_text=_('The name of the tag. '
                                            'Which should be called in a template.'))
    args = models.CharField(_('pass args'), max_length=32, blank=True, null=True,
                            help_text=_('Arguments to pass to the tag when it is '
                                        'called in the template. Comma separated.'
                                        'For example, to pass the key arg for a slider with a set of products, '
                                        'you must specify this key in this field. Only string arguments are supported'))
    wrapper_classes = models.CharField(_('wrapper classes'), max_length=128, blank=True, null=True,
                                       help_text=_('If css classes are specified, '
                                                   'then the content will be displayed inside '
                                                   'the wrapper(with a div tag) with these classes.'))
    without_wrapper = models.BooleanField(_('without wrapper'), default=False,
                                          help_text=_('Don\'t use a wrapper for the block code. '
                                                      'Pass the block code to the template as it is.'))
    bg_color = ColorField(_('background color'), null=True, blank=True)
    bg_image = models.FileField(verbose_name=_('background image'), upload_to='customization/images',
                                validators=[validate_svg_or_image],
                                blank=True, null=True)
    position = models.SmallIntegerField(_('position'), default=0)
    top_indent = models.SmallIntegerField(_('top indent, px'), null=True, blank=True,
                                          help_text=_('Top indent for the block (in pixels).'))
    bottom_indent = models.SmallIntegerField(_('bottom indent, px'), null=True, blank=True,
                                             help_text=_('Bottom indent for the block (in pixels).'))
    enabled = models.BooleanField(_('enabled'), default=True)
    frontpage_only = models.BooleanField(_('frontpage only'), default=False)
    block_title = models.CharField(
        _('block title'), max_length=256, null=True, blank=True)
    title_color = ColorField(_('title font color'), blank=True, null=True)

    class Meta:
        abstract = True
        verbose_name = _('template tag')
        verbose_name_plural = _('template tags')
        ordering = ['position']

    def clean(self):
        if self.bg_color and self.bg_image:
            raise ValidationError(
                _('For the background color of the block, you can choose '
                  'either the color itself or an image that will be used in this capacity, not both.'))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class SliderTagContainerItem(TagContainerItemAbstract):
    """
    Template tag item to display in the slider tag container.
    """
    container = models.ForeignKey(SliderTagContainer,
                                  on_delete=models.CASCADE, related_name='sliders')
    preview_image = models.ImageField(
        _('preview image (admin)'),
        upload_to='customization/admin_tag_previews/',
        blank=True,
        null=True,
        help_text=_('Optional: image for this block in the admin (new_design only).'),
    )

    def __str__(self):
        return self.tag_line or ''


class ColorScheme(models.Model):
    name = models.CharField(_('name'), max_length=128)
    active = models.BooleanField(_('is active'), default=False)
    main_elements_color = ColorField(
        _('main elements color'), null=True, blank=True)
    main_elements_hover_color = ColorField(_('main elements color on hover'),
                                           null=True, blank=True)
    colorless_buttons_border_color = ColorField(_('colorless buttons border color'),
                                                null=True, blank=True)
    colorless_buttons_font_color = ColorField(_('colorless buttons font color'),
                                              null=True, blank=True)
    colorless_buttons_hover_bg = ColorField(_('colorless buttons background on hover'),
                                            null=True, blank=True)
    checkout_button_color = ColorField(_('checkout button color'),
                                       null=True, blank=True)
    checkout_button_font_color = ColorField(_('checkout button font color'),
                                            null=True, blank=True)
    invoice_button_color = ColorField(_('invoice button color'),
                                      null=True, blank=True)
    invoice_button_font_color = ColorField(_('invoice button font color'),
                                           null=True, blank=True)
    header_top_icon_color = ColorField(
        _('header top icon color'), null=True, blank=True)
    header_top_bg_color = ColorField(
        _('header top background color'), null=True, blank=True)
    header_top_menu_font_color = ColorField(
        _('header top menu font color'), null=True, blank=True)
    header_top_menu_font_hover_color = ColorField(
        _('header top menu font hover color'), null=True, blank=True)
    header_top_phone_font_color = ColorField(
        _('header top phone font color'), null=True, blank=True)
    header_bg_color = ColorField(
        _('header background color'), null=True, blank=True)
    frontpage_first_screen_bg_color = ColorField(
        _('frontpage first screen bg color'), null=True, blank=True)
    preview_bg_color = ColorField(_('preview bg color'), null=True, blank=True)
    preview_font_color = ColorField(
        _('preview font color'), null=True, blank=True)
    preview_bg_hover_color = ColorField(
        _('preview bg color on hover'), null=True, blank=True)
    hit_tag_bg_color = ColorField(_('hit tag bg color'), null=True, blank=True)
    hit_tag_font_color = ColorField(
        _('hit tag font color'), null=True, blank=True)
    sale_tag_bg_color = ColorField(
        _('sale tag bg color'), null=True, blank=True)
    sale_tag_font_color = ColorField(
        _('sale tag font color'), null=True, blank=True)
    discount_tag_bg_color = ColorField(
        _('discount tag bg color'), null=True, blank=True)
    discount_tag_font_color = ColorField(
        _('discount tag font color'), null=True, blank=True)
    new_tag_bg_color = ColorField(
        _('is new tag bg color'), null=True, blank=True)
    new_tag_font_color = ColorField(
        _('is new tag font color'), null=True, blank=True)
    news_label_bg_color = ColorField(
        _('news label bg color'), null=True, blank=True)
    news_label_font_color = ColorField(
        _('news label font color'), null=True, blank=True)
    action_label_bg_color = ColorField(
        _('action label bg color'), null=True, blank=True)
    action_label_font_color = ColorField(
        _('action label font color'), null=True, blank=True)
    article_label_bg_color = ColorField(
        _('article label bg color'), null=True, blank=True)
    article_label_font_color = ColorField(
        _('article label font color'), null=True, blank=True)
    search_field_bg_color = ColorField(
        _('search field bg color'), null=True, blank=True)
    search_field_border_color = ColorField(
        _('search field border color'), null=True, blank=True)
    search_field_font_color = ColorField(
        _('search field font color'), null=True, blank=True)
    search_field_placeholder_font_color = ColorField(
        _('search field placeholder font color'), null=True, blank=True)
    header_buttons_font_color = ColorField(
        _('header buttons font color'), null=True, blank=True)
    catalog_menu_bg_color = ColorField(
        _('catalog menu bg color'), null=True, blank=True)
    catalog_menu_hover_bg_color = ColorField(
        _('catalog menu nover bg color'), null=True, blank=True)
    catalog_menu_border_color = ColorField(
        _('catalog menu border color'), null=True, blank=True)
    catalog_menu_font_color = ColorField(
        _('catalog menu font color'), null=True, blank=True)
    catalog_menu_font_hover_color = ColorField(
        _('catalog menu font hover color'), null=True, blank=True)
    catalog_menu_burger_color = ColorField(
        _('catalog menu burger icon color'), null=True, blank=True)
    catalog_menu_arrow_color = ColorField(
        _('catalog menu arrow icon color'), null=True, blank=True)
    catalog_menu_button_bg = ColorField(
        _('catalog menu button background'), null=True, blank=True, help_text='--catalog-menu-button-bg')
    catalog_menu_link_hover = ColorField(
        _('catalog menu link color on hover'), null=True, blank=True, help_text='--catalog-menu-link-hover')

    product_preview_bg_color = ColorField(
        _('product preview bg color'), null=True, blank=True)
    product_preview_border_hover_color = ColorField(
        _('product preview border color on hover'), null=True, blank=True)
    product_list_header_link_color = ColorField(
        _('color for links in product list header'), null=True, blank=True)
    product_list_header_link_hover_color = ColorField(
        _('color for links in product list header on hover'), null=True, blank=True)
    product_tab_link_color = ColorField(
        _('color for product tab links'), null=True, blank=True)
    product_tab_link_hover_color = ColorField(
        _('color for product tab links on hover'), null=True, blank=True)
    breadcrumb_item_color = ColorField(
        _('breadcrumb item color'), null=True, blank=True)
    breadcrumb_item_hover_color = ColorField(
        _('breadcrumb item color on hover'), null=True, blank=True)
    breadcrumb_sep_color = ColorField(
        _('breadcrumb separator color'), null=True, blank=True)
    callme_button_color = ColorField(
        _('color for call-me button'), null=True, blank=True)
    callme_button_hover_color = ColorField(
        _('color for call-me button on hover'), null=True, blank=True)
    callme_button_fill_color = ColorField(
        _('fill color for call-me button'), null=True, blank=True)
    callme_button_fill_hover_color = ColorField(
        _('fill color for call-me button on hover'), null=True, blank=True)
    staticpage_box_fill_color = ColorField(
        _('fill color for staticpage text box'), null=True, blank=True)
    staticpage_box_border_color = ColorField(
        _('border color for staticpage text box'), null=True, blank=True)
    color_lk_accent_items = ColorField(
        _('lk icons color'), null=True, blank=True)

    color_lk_items_bg = ColorField(
        _('bg color for lk item box'), null=True, blank=True)
    color_lk_items_border = ColorField(
        _('color for lk item box border'), null=True, blank=True)
    color_lk_items_hover_bg = ColorField(
        _('bg color for lk item box on hover'), null=True, blank=True)

    color_fixedbtn = ColorField(
        _('color for float fixed buttons'), null=True, blank=True)
    color_bg_fixedbtn = ColorField(
        _('bg for float fixed buttons'), null=True, blank=True)
    color_product_online_price = ColorField(
        _('color for online price'), null=True, blank=True)

    footer_bg_color = ColorField(_('footer bg color'), null=True, blank=True)
    footer_links = ColorField(_('footer links color'), null=True, blank=True)
    footer_links_hover = ColorField(
        _('footer links color on hover'), null=True, blank=True)
    footer_title = ColorField(_('footer title color'), null=True, blank=True)
    custom_font = models.ForeignKey('CustomFont', null=True, blank=True,
                                    verbose_name=_('custom font'),
                                    on_delete=models.SET_NULL)
    custom_font_elements = models.CharField(_('elements with custom font'), max_length=256, null=True, blank=True,
                                            help_text=_('Html elements for which the selected custom font will '
                                                        'be used. Enter separated by commas, the same as when '
                                                        'using the definition of css rules. '
                                                        'Example: h1, h2, .some-css-class, #some-css-id'))

    # MAIN BUTTONS SET
    # primary button
    color_button_primary_text = ColorField(_('button primary text'),
                                           default='#fff',
                                           help_text='--color-button-primary-text')
    color_button_primary_background = ColorField(_('button primary background'),
                                                 default='#2363D1',
                                                 help_text='--color-button-primary-background')
    color_button_primary_border = ColorField(_('button primary border'),
                                             default='#2363D1',
                                             help_text='--color-button-primary-border')
    color_button_primary_text_hover = ColorField(_('button primary text hover'),
                                                 default='#fff',
                                                 help_text='--color-button-primary-text-hover')
    color_button_primary_background_hover = ColorField(_('button primary background hover'),
                                                       default='#1C52AC',
                                                       help_text='--color-button-primary-background-hover')
    color_button_primary_border_hover = ColorField(_('button primary border hover'),
                                                   default='#2363D1',
                                                   help_text='--color-button-primary-border-hover')
    # secondary button
    color_button_secondary_text = ColorField(_('button secondary text'),
                                             default='#2363D1',
                                             help_text='--color-button-secondary-text')
    color_button_secondary_background = ColorField(_('button secondary background'),
                                                   default='#fff',
                                                   help_text='--color-button-secondary-background')
    color_button_secondary_border = ColorField(_('button secondary border'),
                                               default='#B7CBE5',
                                               help_text='--color-button-secondary-border')
    color_button_secondary_text_hover = ColorField(_('button secondary text hover'),
                                                   default='#1C52AC',
                                                   help_text='--color-button-secondary-text-hover')
    color_button_secondary_background_hover = ColorField(_('button secondary background hover'),
                                                         default='#E7EEF6',
                                                         help_text='--color-button-secondary-background-hover')
    color_button_secondary_border_hover = ColorField(_('button secondary border hover'),
                                                     default='#1C52AC',
                                                     help_text='--color-button-secondary-border-hover')
    # muted button
    color_button_muted_text = ColorField(_('button muted text'),
                                         default='#fff',
                                         help_text='--color-button-muted-text')
    color_button_muted_background = ColorField(_('button muted background'),
                                               default='#767676',
                                               help_text='--color-button-muted-background')
    color_button_muted_border = ColorField(_('button muted border'),
                                           default='#767676',
                                           help_text='--color-button-muted-border')
    color_button_muted_text_hover = ColorField(_('button muted text hover'),
                                               default='#fff',
                                               help_text='--color-button-muted-text-hover')
    color_button_muted_background_hover = ColorField(_('button muted background hover'),
                                                     default='#818181',
                                                     help_text='--color-button-muted-background-hover')
    color_button_muted_border_hover = ColorField(_('button muted border hover'),
                                                 default='#818181',
                                                 help_text='--color-button-muted-border-hover')
    # callme button
    color_button_callme_text = ColorField(_('button callme text'),
                                          default='#2363D1',
                                          help_text='--color-button-callme-text')
    color_button_callme_background = ColorField(_('button callme background'),
                                                default='#fff',
                                                help_text='--color-button-callme-background')
    color_button_callme_border = ColorField(_('button callme border'),
                                            default='#B7CBE5',
                                            help_text='--color-button-callme-border')
    color_button_callme_text_hover = ColorField(_('button callme text hover'),
                                                default='#1C52AC',
                                                help_text='--color-button-callme-text-hover')
    color_button_callme_background_hover = ColorField(_('button callme background hover'),
                                                      default='#E7EEF6',
                                                      help_text='--color-button-callme-background-hover')
    color_button_callme_border_hover = ColorField(_('button callme border hover'),
                                                  default='#1C52AC',
                                                  help_text='--color-button-callme-border-hover')
    # cart button
    color_button_cart_text = ColorField(_('button cart text'),
                                        default='#fff',
                                        help_text='--color-button-cart-text')
    color_button_cart_background = ColorField(_('button cart background'),
                                              default='#2363D1',
                                              help_text='--color-button-cart-background')
    color_button_cart_border = ColorField(_('button cart border'),
                                          default='#2363D1',
                                          help_text='--color-button-cart-border')
    color_button_cart_text_hover = ColorField(_('button cart text hover'),
                                              default='#fff',
                                              help_text='--color-button-cart-text-hover')
    color_button_cart_background_hover = ColorField(_('button cart background hover'),
                                                    default='#1C52AC',
                                                    help_text='--color-button-cart-background-hover')
    color_button_cart_border_hover = ColorField(_('button cart border hover'),
                                                default='#2363D1',
                                                help_text='--color-button-cart-border-hover')
    # NEW
    category_preview_height = models.SmallIntegerField(_('category preview height, px'), null=True, blank=True,
                                                       help_text='--category-preview-height')
    color_main_dropdown_menu_bg = ColorField(_('main dropdown menu background'),
                                             default='#333',
                                             help_text='--color-main-dropdown-menu-bg')
    color_main_dropdown_menu_text = ColorField(_('main dropdown menu text color'),
                                               default='#fff',
                                               help_text='--color-main-dropdown-menu-text')

    feedback_form_bg = ColorField(
        _('bg color for feedback form'), null=True, blank=True,
        help_text='--feedback-form-bg')
    feedback_form_section_bg_color = ColorField(
        _('bg color for section block with feedback form'), null=True, blank=True,
        help_text='--feedback-form-section-bg-color')
    feedback_form_title = ColorField(
        _('feedback form: title color'), null=True, blank=True,
        help_text='--feedback-form-title')
    feedback_form_text = ColorField(
        _('feedback form: text color'), null=True, blank=True,
        help_text='--feedback-form-text')
    feedback_form_border = ColorField(
        _('feedback form: border color'), null=True, blank=True,
        help_text='--feedback-form-border')
    feedback_form_input_border = ColorField(
        _('feedback form: input border color'), null=True, blank=True,
        help_text='--feedback-form-input-border')
    search_field_btn_color = ColorField(
        _('search field button color'), null=True, blank=True,
        help_text='--search-field-btn-color ')
    search_field_bg_color = ColorField(
        _('search field bg color'), null=True, blank=True,
        help_text='--search-field-bg-color ')
    search_field_border_color = ColorField(
        _('search field border color'), null=True, blank=True,
        help_text='--search-field-border-color ')
    search_field_font_color = ColorField(
        _('search field font color'), null=True, blank=True, help_text='--search-field-font-color ')
    search_field_placeholder_font_color = ColorField(
        _('search field placeholder font color'), null=True, blank=True,
        help_text='--search-field-placeholder-font-color ')

    inner_page_bg = ColorField(_('inner page background'), null=True,
                               blank=True, help_text='Цвет фона для внутренних страниц.')

    color_card_border = ColorField(_('product teaser border color'),
                                   default='#D9D9DE',
                                   help_text='--color-card-border')
    category_menu_font_highlight_color = ColorField(
        _('category menu font highlight color'), default='#ff5f00',
        help_text='Цвет шрифта при "выделении шрифтом" пункта в выпадающем меню категорий каталога.')
    category_menu_underline_highlight_color = ColorField(
        _('category menu underline highlight color'), default='#ff5f00',
        help_text=('Цвет подчеркивания при "выделении подчеркиванием" '
                   'пункта в выпадающем меню категорий каталога.'))

    VERSION_CACHE_KEY = 'custom_color_scheme_version'

    class Meta:
        verbose_name = _('color scheme')
        verbose_name_plural = _('color schemes')

    def __str__(self):
        return self.name

    def clean(self):
        if self.custom_font and not self.custom_font_elements:
            raise ValidationError(
                _('No html elements selected for display with custom font.'))


class CustomFont(models.Model):
    name = models.SlugField(_('font name'), max_length=60, unique=True,
                            help_text=_('Will be used like font family.'))
    file = models.FileField(_('font file'), upload_to='customization/fonts',
                            validators=[FileExtensionValidator(
                                ALLOWED_FONT_EXTENSIONS_LIST)],
                            help_text=_('Allowed font formats: %(font_formats)s') % {
                                'font_formats': ', '.join(ALLOWED_FONT_EXTENSIONS_LIST)
    })

    class Meta:
        verbose_name = _('custom font')
        verbose_name_plural = _('custom fonts')

    def __str__(self):
        return self.name


class CustomStaticfileAbstract(models.Model):
    active = models.BooleanField(_('active'), default=True)
    position = models.SmallIntegerField(_('position'), default=0)

    class Meta:
        ordering = ['position']
        abstract = True

    def __str__(self):
        return self.name

    @property
    def name(self):
        return self.pk

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class CustomStyle(CustomStaticfileAbstract):
    inline_styles = models.TextField(
        _('inline styles'), blank=True, null=True)
    file = models.FileField(_('custom css file'), upload_to='customization/custom_styles',
                            validators=[FileExtensionValidator(('css',))], blank=True, null=True)

    class Meta(CustomStaticfileAbstract.Meta):
        verbose_name = _('custom css styles')
        verbose_name_plural = _('custom css styles')

    @property
    def name(self):
        if self.file:
            return os.path.basename(self.file.name)
        elif self.inline_styles:
            return Truncator(self.inline_styles).words(4, truncate='...', html=False)

        return f'{self.pk}: no data style'

    def clean(self):
        if not any((self.inline_styles, self.file)):
            raise ValidationError(
                _('You must either set inline styles or load a file with styles.'))


class CustomScript(CustomStaticfileAbstract):
    inline_scripts = models.TextField(
        _('inline scripts'), blank=True, null=True)
    file = models.FileField(_('custom js file'), upload_to='customization/custom_scripts',
                            validators=[FileExtensionValidator(('js',))], blank=True, null=True)

    class Meta(CustomStaticfileAbstract.Meta):
        verbose_name = _('custom js script')
        verbose_name_plural = _('custom js scripts')

    @property
    def name(self):
        if self.file:
            return os.path.basename(self.file.name)
        elif self.inline_scripts:
            return Truncator(self.inline_scripts).words(4, truncate='...', html=False)

        return f'{self.pk}: no data js'

    def clean(self):
        if not any((self.inline_scripts, self.file)):
            raise ValidationError(
                _('You must either set inline js or load a file with scripts.'))


class CustomTemplateBlock(models.Model):
    """
    Block for a tag containers with a custom django template code.
    """
    key = models.SlugField(_('key'), max_length=70, primary_key=True)
    name = models.CharField(_('name'), max_length=128)
    code = models.TextField(_('template code'))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('custom template block')
        verbose_name_plural = _('custom template blocks')


class MobileMenuButton(MPTTModel):
    name = models.CharField(_('Name'), max_length=128)
    active = models.BooleanField(_('Active'), default=True)
    type = models.CharField(
        _('Type'),
        choices=(
            ('static', _('Static')),
            ('cart', _('Cart')),
            ('comparision', _('Comparision')),
            ('favorite', _('Favorite')),
            ('additional_menu', _('Additional menu'))
        ),
        max_length=15
    )
    url = models.CharField(_('URL'), max_length=255, blank=True)
    icon_default = models.FileField(_('Icon default'), upload_to='costomization/mobile/menu/', blank=True)
    icon_active = models.FileField(_('Icon active'), upload_to='costomization/mobile/menu/', blank=True)
    parent = TreeForeignKey('self', verbose_name=_('parent'), null=True, blank=True, related_name='children',
                            db_index=True, on_delete=models.SET_NULL,
                            help_text=_('Parent category (if any).'))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('mobile menu button')
        verbose_name_plural = _('mobile menu buttons')
        ordering = ('lft', 'name')
