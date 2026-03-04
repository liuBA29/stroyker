from django.db import models
from django.utils.translation import ugettext as _


class Scraper(models.Model):
    """ Scraper for product parsing. """
    partner = models.ForeignKey('addresses.Partner', on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey('catalog.Category', on_delete=models.CASCADE, null=True, blank=True)
    category_source_url = models.URLField(_('source url'), max_length=1024)
    parameters_to_parse = models.CharField(_('parameters to parse'), max_length=255, null=True)
    filter_option_selector = models.CharField(_('filter option selector'), max_length=50)
    filter_json_attr = models.CharField(_('filter json data attribute'), max_length=50, null=True, blank=True)
    filter_option_title_selector = models.CharField(_('filter option title selector'), max_length=50)
    filter_option_checkbox_selector = models.CharField(_('filter option checkbox selector'), max_length=50)
    filter_option_range_selector = models.CharField(_('filter option range selector'), max_length=50,
                                                    null=True, blank=True)
    filter_parameter_names_to_walk = models.CharField(_('filter parameter names to walk'),
                                                      max_length=1024, null=True, blank=True)
    filter_product_to_walk_selector = models.CharField(_('filter product to walk selector'), max_length=50,
                                                       null=True, blank=True)
    pagination_selector = models.CharField(_('pagination item selector'), max_length=50, null=True, blank=True)
    page_prefix = models.CharField(_('page prefix'), max_length=50, null=True, blank=True)
    product_url_selector = models.CharField(_('product url selector'), max_length=50)
    product_code_selector = models.CharField(_('product code selector'), max_length=50, null=True, blank=True)
    product_price_selector = models.CharField(_('price selector'), max_length=50)
    product_name_selector = models.CharField(_('product name selector'), max_length=50)
    product_description_selector = models.CharField(_('product description selector'), max_length=50)
    product_inline_params_selector = models.CharField(_('product inline params selector'), max_length=50)
    product_inline_params_map = models.CharField(_('product inline params map'), max_length=255)
    product_image_selector = models.CharField(_('product image selector'), max_length=50, null=True, blank=True)
    product_image_src_attr = models.CharField(_('product image src attribute'), max_length=50, null=True, blank=True)
    product_old_images_delete = models.BooleanField(_('delete product old images'), default=True)
    product_uom_name = models.CharField(_('product unit name'), max_length=20)
    product_published = models.BooleanField(_('product published'), default=False)
    product_parameters_to_join = models.CharField(_('parameters to join'), max_length=1024, null=True, blank=True)
    product_parameter_values_to_join = models.CharField(_('parameter values to join'),
                                                        max_length=1024, null=True, blank=True)
    product_params_clear = models.BooleanField(_('clear params of existed products'), default=True)

    class Meta:
        unique_together = (('category', 'partner'), )
        verbose_name = _('scraper')
        verbose_name_plural = _('scrapers')
