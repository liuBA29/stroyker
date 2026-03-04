import math

from django import forms
from django.db.models import Q, Count
from django.utils.translation import ugettext as _
from django.utils.html import mark_safe

from stroykerbox.apps.catalog.widgets import (
    RangeWidget,
    RangeField,
    MultiChoiceFilterWidget,
)
from stroykerbox.apps.locations.models import Location
from constance import config

from .models import Parameter, ProductParameterValueMembership, ProductStockAvailability


class FilterForm(forms.Form):
    """
    Catalog filter form
    """

    def get_stock_avail_choices_list(self):
        categories_list = [self.category]
        if config.CATALOG_SHOW_CHILDS_IN_PARENT:
            categories_list += list(self.category.get_published_children())
        qs = ProductStockAvailability.objects.filter(
            product__categories__in=categories_list, product__published=True
        )
        if self.location:
            qs = qs.filter(warehouse__location=self.location)

        label = f'warehouse__{config.CATALOG_STOCK_FILTER_NAME_FIELD}'
        qs = (
            qs.values('warehouse_id', label)
            .annotate(avail=Count('id'))
            .order_by('warehouse__position')
        )
        return [
            (r['warehouse_id'], mark_safe(f'{r[label]} <span>{r["avail"]}</span>'))
            for r in qs
        ]

    def __init__(self, category, location=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.category = category
        self.location = location
        self.has_filters = False

        # Contains all form's parameters as dict of parameter's slug and name pairs
        self.param_names_by_slug = {}
        # Contains all form's choices as dict of choice's slug and name pairs
        self.choice_names_by_slug = {}

        category_parameters = category.get_category_paremeters

        if config.CATALOG_STOCK_FILTER:
            stock_choices = self.get_stock_avail_choices_list()
            if stock_choices and len(stock_choices) > 1:
                self.fields['stock_avail'] = forms.MultipleChoiceField(
                    widget=MultiChoiceFilterWidget,
                    choices=stock_choices,
                    label=config.CATALOG_STOCK_FILTER_LABEL,
                )
                self.fields['stock_avail'].required = False

        # Keep the list of all range fields to validate them in the clean() method below.
        self.range_field_names = ['price_range']
        # Collect fields are always expanded.
        self.expanded_fields = []
        if category_parameters:
            self.has_filters = True
            for parameter, expanded in category_parameters:
                # add parameter's slug and name to param_names_by_slug field
                self.param_names_by_slug[parameter.slug] = parameter.name
                # add category specific fields
                choices = [
                    val for val in parameter.get_parameter_choices(category) if val[1]
                ]
                if choices:
                    # add choice's slug and name to choice_names_by_slug field
                    for slug, value in choices:
                        self.choice_names_by_slug[slug] = value

                    if parameter.widget == 'radio':
                        widget = forms.RadioSelect()
                        field = forms.ChoiceField(
                            widget=widget,
                            required=False,
                            label=parameter.name,
                            choices=choices,
                        )
                    elif parameter.widget == 'checkbox':
                        # change default choices when filter has only one value
                        if len(choices) == 1:
                            # get original value from choices and change label to parameter name
                            choices = [
                                (choices[0][0], '{}'.format(format(choices[0][1])))
                            ]
                        widget = MultiChoiceFilterWidget
                        field = forms.MultipleChoiceField(
                            widget=widget,
                            required=False,
                            label=parameter.name,
                            choices=choices,
                        )
                    elif parameter.widget == 'range':
                        choices = sorted(choices, key=lambda x: x[0])

                        value_0 = float(self.data.get(f'{parameter.slug}_0', 0))
                        value_1 = float(self.data.get(f'{parameter.slug}_1', 0))

                        min_value = choices[0][0] if choices else 0
                        max_value = choices[-1][0] if choices else 0

                        widget = RangeWidget(
                            widgets=(
                                forms.TextInput(
                                    attrs={
                                        'class': 'range-input',
                                        'data-current-value': math.floor(
                                            value_0 or min_value
                                        ),
                                        'data-min-value': math.floor(min_value),
                                        'disabled': False,
                                    }
                                ),
                                forms.TextInput(
                                    attrs={
                                        'class': 'range-input',
                                        'data-current-value': math.ceil(
                                            value_1 or max_value
                                        ),
                                        'data-max-value': math.ceil(max_value),
                                        'disabled': False,
                                    }
                                ),
                            )
                        )
                        field = RangeField(
                            forms.IntegerField,
                            widget=widget,
                            label=parameter.name,
                            required=False,
                        )
                        self.range_field_names.append(parameter.slug)
                    else:
                        widget = forms.Select(attrs={'class': 'custom-select'})
                        choices = [('', _('-----------'))] + choices
                        field = forms.ChoiceField(
                            widget=widget,
                            required=False,
                            label=parameter.name,
                            choices=choices,
                        )
                    self.fields[parameter.slug] = field

                    # https://redmine.fancymedia.ru/issues/12507
                    if (not self.data and expanded) or (parameter.slug in self.data):
                        self.expanded_fields.append(parameter.slug)
                else:
                    continue

        # add price range field
        # checking for filters in the current request
        price_range_0, price_range_1 = self.data.get('price_range_0'), self.data.get(
            'price_range_1'
        )
        self.products_price_agg = self.category.get_descendant_products_price_agg(
            self.location
        )
        min_price, max_price = (
            self.products_price_agg['price__min'] or 0,
            math.ceil(self.products_price_agg['price__max'] or 0),
        )
        range_widget = RangeWidget(
            widgets=(
                forms.TextInput(  # init of the global and current min value for noUiSlider
                    attrs={
                        'class': 'range-input',
                        'data-current-value': int(price_range_0 or min_price),
                        'data-min-value': int(min_price),
                    }
                ),
                forms.TextInput(  # init of the global and current max value for noUiSlider
                    attrs={
                        'class': 'range-input',
                        'data-current-value': int(price_range_1 or max_price),
                        'data-max-value': int(max_price),
                    }
                ),
            )
        )
        self.fields['price_range'] = RangeField(
            forms.IntegerField, widget=range_widget, label=_('Price'), required=False
        )
        self.fields['price_sorting'] = forms.CharField(
            widget=forms.HiddenInput, required=False
        )

    def clean(self):
        cleaned_data = super(FilterForm, self).clean()
        # Validate range fields.
        for field_name in self.range_field_names:
            range_values = cleaned_data.get(field_name)
            # If range field has just one value raise ValidationError
            if range_values is not None and any(
                value is None for value in range_values
            ):
                self.add_error(field_name, _('Enter both values'))

    def get_filtered_products(self):
        """
        Get products by the currently chosen parameters in filter.
        Use only for a valid form.
        """
        products = self.category.get_descendant_products()

        price_range = self.cleaned_data.pop('price_range', None)
        stock_avail = self.cleaned_data.pop('stock_avail', None)

        if stock_avail:
            avail_products = ProductStockAvailability.objects.filter(
                warehouse__in=stock_avail, available__gt=0
            ).values_list('product_id', flat=True)
            products = products.filter(id__in=avail_products)

        if Location.check_default(self.location):
            if price_range:
                default_location = Location.get_default_location()
                products = products.filter(
                    Q(price__range=price_range)
                    | (
                        Q(location_prices__location=default_location)
                        & Q(location_prices__price__range=price_range)
                    )
                )
        elif price_range:
            if price_range:
                products = products.filter(
                    location_prices__location=self.location,
                    location_prices__price__range=price_range,
                )

        price_sorting = self.cleaned_data.pop('price_sorting', None)
        if price_sorting:
            if price_sorting == 'asc':
                products = products.order_by('price')
            else:
                products = products.order_by('-price')

        for param_slug, value in self.cleaned_data.items():
            if value is not None and len(value) > 0:
                parameter = Parameter.objects.get(slug=param_slug)
                filter_fields = {'params__parameter': parameter}

                if parameter.data_type == 'decimal':
                    value_field = 'params__value_decimal'
                else:
                    value_field = 'params__parameter_value__value_slug'

                if parameter.widget == 'checkbox':
                    filter_fields[f'{value_field}__in'] = value
                elif parameter.widget == 'range':
                    parameters = ProductParameterValueMembership.objects.filter(
                        product__in=products,
                        parameter=parameter,
                        value_decimal__range=value,
                    )
                    products = products.filter(params__in=parameters)
                else:
                    # radio and select widgets have single values
                    filter_fields[value_field] = value
                products = products.filter(**filter_fields)
        return products


class ImportBaseForm(forms.Form):
    file = forms.FileField()


class ImportRelatedProductsForm(ImportBaseForm):
    rewrite = forms.BooleanField(
        label='Перезапись связей у товара',
        required=False,
        help_text=(
            'Перезаписывать связи у товара из файла импорта. '
            'Все "старые" связи будут удалены(заменены связями, '
            'прописанными в файле импорта). '
            'Если не отмечено, тогда связи из импорта будут лишь добавлены к уже существующим у товара.'
        ),
    )


class DocImportForm(ImportBaseForm):
    delete_old = forms.BooleanField(
        label='',
        required=False,
        help_text=_('Удалять перед импортом все другие документы товара.'),
    )


class ExportBaseForm(forms.Form):
    output_format = forms.ChoiceField(
        widget=forms.RadioSelect, choices=[(f, f) for f in ('xls', 'xlsx')]
    )


class ProductParameterValueImportForm(ImportBaseForm):
    delete_before = forms.BooleanField(
        label='',
        required=False,
        help_text=_('Удалять перед импортом все имеющиеся у товара параметры.'),
    )


class ProductImagesImportForm(ImportBaseForm):
    IMAGE_EXTENSIONS_FOR_SELECT = ('jpg', 'jpeg', 'png', 'webp')

    has_headers = forms.BooleanField(
        label='',
        required=False,
        help_text='Файл содержит заголовки для каждой колонки.',
        initial=True,
    )

    rewrite_images = forms.BooleanField(
        label='', required=False, help_text='Перезаписывать картинки', initial=False
    )

    resize_width = forms.IntegerField(
        label='Обрезать по ширине, в px',
        required=False,
        help_text=_(
            'Если указано, тогда загружаемые изображения будут обрезаться '
            'по широкой стороне под полученное значение.'
        ),
    )
    extension = forms.ChoiceField(
        label='Добавлять расширение',
        choices=[('', 'Не добавлять')] + [(e, e) for e in IMAGE_EXTENSIONS_FOR_SELECT],
        required=False,
    )


class ProductPropsImportForm(ImportBaseForm):
    rewrite_props = forms.BooleanField(
        label='',
        required=False,
        help_text=_('Перезаписывать cуществующие свойства'),
        initial=False,
    )


class PriceFromFeedUpdForm(forms.Form):
    sku = forms.ChoiceField(
        label='Поле артикула', choices=[(i, i) for i in ('offerId', 'vendorCode')]
    )
    url = forms.URLField(label='URL фида')


class ReplaceSkuFromFileForm(forms.Form):
    file = forms.FileField(label='Файл с данными для замены')
