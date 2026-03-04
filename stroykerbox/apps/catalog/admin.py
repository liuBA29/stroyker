# mypy: ignore-errors
from io import StringIO
import uuid

from PIL import UnidentifiedImageError
import django
from django.contrib import admin, messages
from django.conf import settings
from django.utils.translation import ugettext as _
from django.utils.timezone import now
from django.db import IntegrityError
from django.db.models import Q, ManyToManyField, Sum, IntegerField
from django.db.models.functions import Coalesce
from django.utils.html import format_html
from django import forms
from django.urls import path, reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.shortcuts import render
from django.utils.html import mark_safe
from ckeditor.widgets import CKEditorWidget

from . import resources
from .admin_actions import set_categories
from .import_export import (
    productparametervaluemembership_export,
    productparametervaluemembership_import,
    import_parameter_values,
    export_parameter_values,
    product_images_import,
    product_doc_import,
    product_doc_export,
    product_props_import,
    product_props_export,
    product_related_export,
    product_related_import,
    update_prices_from_feed,
    replace_product_sku,
)


from import_export.admin import ImportExportModelAdmin, ImportMixin
from import_export.formats import base_formats
from sorl.thumbnail import get_thumbnail
from sorl.thumbnail.admin import AdminImageMixin
from mptt.admin import DraggableMPTTAdmin
from constance import config
from stroykerbox.apps.catalog import models
from stroykerbox.apps.utils.watermark import create_watermark
from stroykerbox.apps.floatprice.models import FloatPrice
from stroykerbox.apps.custom_forms.utils import custom_form_help_text

from .admin_filters import MultipleChoiceListFilter
from .forms import (
    ExportBaseForm,
    DocImportForm,
    ImportRelatedProductsForm,
    ProductParameterValueImportForm,
    ProductImagesImportForm,
    ProductPropsImportForm,
    PriceFromFeedUpdForm,
    ImportBaseForm,
    ReplaceSkuFromFileForm,
)


class CollapsedMixin:
    classes = ('collapse',)


@admin.register(models.Uom)
class UomAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = resources.UomImportResource
    search_fields = ('name',)


@admin.register(models.PriceType)
class PriceTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


class ParameterValueInline(CollapsedMixin, admin.TabularInline):
    model = models.ParameterValue
    prepopulated_fields = {'value_slug': ('value_str',)}
    extra = 0


class ProductPropsInline(CollapsedMixin, admin.TabularInline):
    model = models.ProductProps
    prepopulated_fields = {'slug': ('name',)}
    extra = 0


class ProductRefInline(CollapsedMixin, admin.TabularInline):
    model = models.ProductRelated
    raw_id_fields = ('product',)
    fk_name = 'ref'
    autocomplete_fields = ['product']
    extra = 0
    sortable_field_name = 'position'
    ordering = ('position',)


@admin.register(models.Parameter)
class ParameterAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = resources.ParameterImportResource
    list_display = ('name', 'slug', 'data_type', 'widget', 'position')
    prepopulated_fields = {'slug': ['name']}
    inlines = (ParameterValueInline,)
    search_fields = (
        'name',
        'slug',
    )
    list_editable = ('position',)
    change_form_template = "catalog/admin/parameter_change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'parameter_values_export/<int:parameter_pk>/',
                self.parameter_values_export,
                name='parameter_values_export',
            ),
            path(
                'parameter_values_import/<int:parameter_pk>/',
                self.parameter_values_import,
                name='parameter_values_import',
            ),
        ]
        return custom_urls + urls

    def parameter_values_export(self, request, parameter_pk):
        parameter = self.get_object(request, parameter_pk)
        if parameter:
            output_format = 'xls'
            data = export_parameter_values(parameter_pk, output_format)
            if data:
                filename = f'parameter_{parameter.slug.upper()}_values_export_{now().strftime("%Y-%m-%d")}.{output_format}'  # noqa

                response = HttpResponse(
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename={filename}'
                response.write(data)
                return response
        else:
            self.message_user(
                request, f'Параметер с ID {parameter_pk} не найден.', 'ERROR'
            )

        return HttpResponseRedirect(
            reverse('admin:catalog_parameter_change', args=[parameter_pk])
        )

    def parameter_values_import(self, request, parameter_pk):

        if request.method == 'POST':
            form = ImportBaseForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['file']
                result_dict = import_parameter_values(parameter_pk, file)
                if result_dict:
                    for level_str in result_dict.keys():
                        for msg in result_dict[level_str]:
                            self.message_user(
                                request, msg, getattr(messages, level_str, 'INFO')
                            )
                    return HttpResponseRedirect(
                        reverse('admin:catalog_parameter_change', args=[parameter_pk])
                    )

        parameter = self.get_object(request, parameter_pk)

        if not parameter:
            self.message_user(
                request, f'Параметер с ID {parameter_pk} не найден.', 'ERROR'
            )
            return HttpResponseRedirect(
                reverse('admin:catalog_parameter_change', args=[parameter_pk])
            )
        form = ImportBaseForm()
        context = {'form': form, 'parameter': parameter}
        return render(request, 'catalog/admin/parameter_values_import.html', context)


@admin.register(models.ParameterValue)
class ParameterValueAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = resources.ParameterValueImportResource
    search_fields = ('value_str', 'parameter__name')


class CategoryParameterMembershipInline(CollapsedMixin, admin.TabularInline):
    model = models.CategoryParameterMembership
    sortable_field_name = 'position'
    extra = 0


class CategoryAdminForm(forms.ModelForm):

    vk_group_id = forms.ChoiceField(choices=[(0, _('Не задано'))], required=False)

    class Meta:
        model = models.Category
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vk_group_id'].choices += self.get_vk_category_choices()

    def get_vk_category_choices(self):
        choices = []
        try:
            from stroykerbox.apps.vk_market.models import VKCategory
        except Exception:
            pass
        else:
            try:
                choices = [
                    (id, f'{name} ({s_name})')
                    for id, name, s_name in VKCategory.objects.values_list(
                        'id', 'name', 'section_name'
                    )
                ]
            except Exception:
                pass
        return choices


@admin.register(models.Category)
class CategoryAdmin(ImportExportModelAdmin, AdminImageMixin, DraggableMPTTAdmin):
    form = CategoryAdminForm
    list_display = (
        'tree_actions',
        'indented_title',
        'slug',
        'preview',
        'is_container',
        'published',
        'maybeinterested_block',
        'online_discount',
    )
    list_display_links = ('indented_title',)
    list_editable = ('published', 'maybeinterested_block')
    prepopulated_fields = {'slug': ('name',)}
    inlines = (CategoryParameterMembershipInline,)
    actions = ('set_published', 'set_unpublished')

    search_fields = ('name',)
    # autocomplete_fields = ('related_categories',)

    change_list_template = "catalog/admin/categories_changelist.html"

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'name',
                    'parent',
                    'highlight',
                    'is_container',
                    'products_per_row',
                    'list_as_rows',
                    'maybeinterested_block',
                    'image',
                    'svg_image',
                    'slug',
                    'published',
                    'icon',
                    'seo_text',
                    'related_categories',
                    'online_discount',
                    'sidebar_siblings',
                    'vk_group_id',
                )
            },
        ),
    )

    def get_import_resource_class(self):
        return resources.CategoryImportResource

    def get_export_resource_class(self):
        return resources.CategoryExportResource

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        only_fields = (
            'name',
            'slug',
            'is_container',
            'published',
            'maybeinterested_block',
        )
        return qs.only(*only_fields)

    def preview(self, obj):
        if obj.image_file:
            if obj.image:
                try:
                    thumb = get_thumbnail(obj.image_file, '100x100', quality=80)
                except IOError as e:
                    return 'Image error: %s' % str(e)
            elif obj.svg_image:
                thumb = obj.svg_image
            return format_html('<img width="100" height="100" src="%s" />' % thumb.url)
        return ''

    preview.short_description = _('preview')
    preview.allow_tags = True

    def set_published(self, request, queryset):
        queryset.filter(published=False).update(published=True)

    set_published.short_description = _('Set as published')

    def set_unpublished(self, request, queryset):
        queryset.filter(published=True).update(published=False)

    set_unpublished.short_description = _('Set as unpublished')

    def get_urls(self):
        new_url = [
            path(
                'mptt_run_categories_rebuild/',
                self.run_mppt_categories_rebuild,
                name='mppt_categories_rebuild',
            ),
        ]
        return new_url + super().get_urls()

    def run_mppt_categories_rebuild(self, request):
        stdout, stderr = StringIO(), StringIO()

        call_command(
            'mptt_category_rebuild', '--no-color', stdout=stdout, stderr=stderr
        )
        if err_msg := stderr.getvalue():
            self.message_user(request, err_msg, 'ERROR')

        if msg := stdout.getvalue():
            self.message_user(request, msg, 'INFO')
        return HttpResponseRedirect(reverse('admin:catalog_category_changelist'))


@admin.register(models.CategoryParameterMembership)
class CategoryParameterMembershipAdmin(ImportMixin, admin.ModelAdmin):
    resource_class = resources.CategoryParameterMembershipImportResource


class ProductsWithoutDescriptionFilter(admin.SimpleListFilter):
    title = _('описание товара')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'description'

    def lookups(self, request, model_admin):
        return (
            ('not_empty', _('заполнено')),
            ('empty', _('не заполнено')),
        )

    def queryset(self, request, queryset):
        f = Q(description='')
        if self.value() == 'not_empty':
            return queryset.exclude(f)
        if self.value() == 'empty':
            return queryset.filter(f)


class ProductsWithoutPriceFilter(admin.SimpleListFilter):
    title = _('цена товара')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'price'

    def lookups(self, request, model_admin):
        return (
            ('not_empty', _('не нулевая')),
            ('empty', _('нулевая')),
        )

    def queryset(self, request, queryset):
        f = Q(price=0) | Q(price__isnull=True)
        if self.value() == 'not_empty':
            return queryset.exclude(f)
        if self.value() == 'empty':
            return queryset.filter(f)


class ProductImagesInlineAdmin(CollapsedMixin, admin.TabularInline):
    model = models.ProductImage
    verbose_name_plural = _('product images')

    fields = ('image', 'preview', 'position')
    readonly_fields = ('preview',)
    extra = 0

    def preview(self, obj):
        if obj.image:
            try:
                thumb = get_thumbnail(obj.image, '100x100', quality=80)
            except IOError as e:
                return 'Image error: %s' % str(e)
            else:
                return format_html('<img src="%s" />' % thumb.url)
        return ''

    preview.short_description = _('preview')
    preview.allow_tags = True


class ProductCertificateInline(CollapsedMixin, admin.TabularInline):
    model = models.ProductCertificate
    verbose_name_plural = _('product certificate')

    fields = ('name', 'file')
    extra = 0


class ProductParameterValueMembershipInline(CollapsedMixin, admin.TabularInline):
    model = models.ProductParameterValueMembership
    extra = 0
    sortable_field_name = 'position'

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):

        if db_field.name == 'parameter':
            product_pk = None
            if request.resolver_match.args:
                product_pk = request.resolver_match.args[0]
            if request.resolver_match.kwargs:
                product_pk = request.resolver_match.kwargs['object_id']
            # filter parameter drop down values by CategoryParameterMembership
            if product_pk:
                product = models.Product.objects.get(pk=product_pk)
                category_pks = {
                    c.get_first_ancestor_with_filters()
                    for c in product.categories.all()
                    if product.category
                }
                if None in category_pks:
                    category_pks.remove(None)
                kwargs['queryset'] = models.Parameter.objects.filter(
                    categoryparametermembership__category__in=category_pks
                ).distinct()

        return super(
            ProductParameterValueMembershipInline, self
        ).formfield_for_foreignkey(db_field, request, **kwargs)


class ProductStockAvailabilityInline(CollapsedMixin, admin.TabularInline):
    model = models.ProductStockAvailability
    extra = 0


class ProductLocationPriceInline(CollapsedMixin, admin.TabularInline):
    model = models.ProductLocationPrice
    extra = 0


class EmptyCategoryListFilter(MultipleChoiceListFilter):
    title = _('Наличие или отсутствие категории')

    parameter_name = 'has_categories'

    def lookups(self, request, model_admin):

        return (
            ('yes', _('Yes')),
            ('no', _('No')),
        )

    def queryset(self, request, queryset):

        if self.value() == 'yes':
            return queryset.filter(categories__isnull=False)

        if self.value() == 'no':
            return queryset.filter(categories__isnull=True)


class CategoryListFilter(MultipleChoiceListFilter):
    title = _('Категории')
    parameter_name = 'categories__in'

    def lookups(self, request, model_admin):
        return models.Category.objects.values_list('pk', 'name')


class FloatPriceInline(admin.TabularInline):
    model = FloatPrice
    extra = 0


@admin.register(models.Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = resources.ProductExportResource
    list_max_show_all = settings.LIST_MAX_SHOW_ALL_FOR_PRODUCT_LIST
    list_per_page = getattr(
        settings, 'ADMIN__PRODUCT_PER_PAGE', config.ADMIN__PRODUCT_PER_PAGE
    )
    list_display = [
        'name',
        'sku',
        'price',
        'old_price',
        'updated_at',
        'published',
        'available',
        'yml_export',
        'position',
    ]
    list_editable = (
        'position',
        'price',
        'old_price',
        'yml_export',
    )
    list_filter = (
        EmptyCategoryListFilter,
        CategoryListFilter,
        ProductsWithoutDescriptionFilter,
        ProductsWithoutPriceFilter,
        'published',
        'is_sale',
        'is_hit',
        'is_new',
        'yml_export',
        'price_in_compete',
    )
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('sku', 'name')
    actions = [
        'set_published',
        'set_unpublished',
        'set_price_in_compete',
        'unset_price_in_compete',
        'set_is_hit',
        'unset_is_hit',
        'set_is_new',
        'unset_is_new',
        'set_is_sale',
        'unset_is_sale',
        'set_as_discounted',
        'unset_as_discounted',
        'set_is_action',
        'unset_is_action',
        set_categories,
        'set_yml_export',
        'unset_yml_export',
    ]
    change_form_template = "catalog/admin/product_change_form.html"
    change_list_template = "catalog/admin/products_changelist.html"
    mptt_level_indent = 20
    formfield_overrides = {
        ManyToManyField: {'widget': forms.CheckboxSelectMultiple},
    }

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'name',
                    'short_description',
                    'description',
                    'use_editor',
                    'search_words',
                    'sku',
                    'third_party_code',
                    'slug',
                    'categories',
                    'currency',
                    'price',
                    'price_in_compete',
                    'price_from',
                    'price_from_to',
                    'old_price',
                    'purchase_price',
                    'multiplicity',
                    'multiplicity_label',
                    'uom',
                    'price_type',
                    'days_to_arrive',
                    'is_hit',
                    'is_new',
                    'is_sale',
                    'discounted',
                    'is_action',
                    'weight',
                    'volume',
                    'length',
                    'width',
                    'height',
                    'published',
                    'yml_export',
                    'modification_code',
                    'vk_market',
                    'position',
                )
            },
        ),
        (
            'Описание 2',
            {
                'fields': ('description2',),
                'classes': ('collapse',),
            },
        ),
    )

    inlines = (
        ProductRefInline,
        ProductStockAvailabilityInline,
        ProductLocationPriceInline,
        ProductImagesInlineAdmin,
        ProductCertificateInline,
        ProductParameterValueMembershipInline,
        ProductPropsInline,
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        for f in ('description', 'description2'):
            form.base_fields[f].help_text += f'<p>{custom_form_help_text}</p>'
            if not obj or obj.use_editor:
                # https://redmine.nastroyker.ru/issues/16261
                form.base_fields[f].widget = CKEditorWidget()
        return form

    def get_import_resource_class(self):
        return resources.ProductImportResource

    def get_urls(self):
        urls = super().get_urls()
        return [
            path(
                'product_clone/<int:product_pk>/',
                self.product_clone,
                name='product_clone',
            ),
            path('apply_watermarks/', self.apply_watermarks, name='apply_watermarks'),
            path(
                'update_search_index/',
                self.update_search_index,
                name='update_search_index',
            ),
            path('images_import/', self.images_import, name='product_images_import'),
            path('doc_import/', self.doc_import, name='product_doc_import'),
            path('doc_export/', self.doc_export, name='product_doc_export'),
            path('props_import/', self.props_import, name='product_props_import'),
            path('props_export/', self.props_export, name='product_props_export'),
            path(
                'vk-sync-all/',
                self.admin_site.admin_view(self.vk_sync_all),
                name='vk_sync_all',
            ),
            path(
                'vk-sync-product/<int:product_id>/',
                self.admin_site.admin_view(self.vk_sync_product),
                name='vk_sync_product',
            ),
            path('related_export/', self.related_export, name='product_related_export'),
            path('related_import/', self.related_import, name='product_related_import'),
            path(
                'price_update_from_feed/',
                self.price_update_from_feed,
                name='price_update_from_feed',
            ),
            path('replace_sku/', self.replace_sku, name='replace_sku'),
        ] + urls

    def replace_sku(self, request):
        """
        Переписывание артикулов из файла.
        https://redmine.nastroyker.ru/issues/15822
        """
        if request.method == 'POST':
            form = ReplaceSkuFromFileForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['file']
                result_dict = replace_product_sku(file)
                for level_key, msg in result_dict.items():
                    self.message_user(request, msg, level_key)
                return HttpResponseRedirect(reverse('admin:catalog_product_changelist'))

        form = ReplaceSkuFromFileForm()
        context = {'form': form}
        return render(request, 'catalog/admin/replace_products_sku.html', context)

    def related_export(self, request):
        qs = self.get_export_queryset(request)
        data = product_related_export(qs, 'xls')
        filename = f'product_related_export_{now().strftime("%Y-%m-%d")}.xls'
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        response.write(data)
        return response

    def related_import(self, request):
        if request.method == 'POST':
            form = ImportRelatedProductsForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['file']
                rewrite = form.cleaned_data['rewrite']
                result_dict = product_related_import(file, rewrite)
                if result_dict:
                    for msg in result_dict.get('INFO', []):
                        self.message_user(request, msg, 'INFO')
                    for msg in result_dict.get('ERROR', []):
                        self.message_user(request, msg, 'ERROR')
            return HttpResponseRedirect(reverse('admin:catalog_product_changelist'))

        form = ImportRelatedProductsForm()
        context = {'form': form}
        return render(request, 'catalog/admin/product_related_import.html', context)

    def doc_export(self, request):
        qs = self.get_export_queryset(request).filter(certificates__isnull=False)
        data = product_doc_export(qs, 'xls')
        filename = f'product_doc_export_{now().strftime("%Y-%m-%d")}.xls'

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        response.write(data)
        return response

    def doc_import(self, request):
        if request.method == 'POST':
            form = DocImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['file']
                result_dict = product_doc_import(
                    file, delete_old=form.cleaned_data.get('delete_old')
                )
                if result_dict:
                    for msg in result_dict.get('INFO', []):
                        self.message_user(request, msg, 'INFO')
                    for msg in result_dict.get('ERROR', []):
                        self.message_user(request, msg, 'ERROR')

            return HttpResponseRedirect(reverse('admin:catalog_product_changelist'))
        form = DocImportForm()
        context = {'form': form}
        return render(request, 'catalog/admin/product_doc_import.html', context)

    def get_export_formats(self):
        return (base_formats.XLSX,)

    def get_inlines(self, request, obj=None):
        inlines = super().get_inlines(request, obj)
        if config.FLOATPRICE_IS_ACTIVE:
            inlines = [FloatPriceInline] + list(inlines)
        return inlines

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if getattr(obj, 'price_in_compete', None):
            fields.append('price')
        return fields

    @admin.display(description=_('Выгружать в YML'))
    def set_yml_export(self, request, queryset):
        queryset.filter(yml_export=False).update(yml_export=True)

    @admin.display(description=_('Убрать выгрузку в YML'))
    def unset_yml_export(self, request, queryset):
        queryset.filter(yml_export=True).update(yml_export=False)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        self.request = request
        qs = qs.annotate(
            available=Coalesce(
                Sum('stocks_availability__available'), 0, output_field=IntegerField()
            )
        )
        return qs

    def available(self, obj):
        return obj.available

    available.short_description = _('product availability in stock')
    available.admin_order_field = 'available'

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['watermarks_allowed'] = all(
            [
                config.WATERMARK_PRODUCT_IMAGES,
                config.WATERMARK_FILE,
                models.ProductImage.objects.filter(has_watermarked=False).exists(),
            ]
        )
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description=_('Set as published'))
    def set_published(self, request, queryset):
        if queryset.filter(categories__isnull=True).exists():
            message = _('A published product must be assigned a category.')
            self.message_user(request, message)

        result = models.Product.objects.filter(
            id__in=queryset.values_list('id', flat=True),
            categories__isnull=False,
            published=False,
        ).update(published=True)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    @admin.display(description=_('Set as unpublished'))
    def set_unpublished(self, request, queryset):
        result = models.Product.objects.filter(
            id__in=queryset.values_list('id', flat=True), published=True
        ).update(published=False)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    @admin.display(description=_('Установить флаг "цена в конкуренции"'))
    def set_price_in_compete(self, request, queryset):
        result = queryset.filter(price_in_compete=False).update(price_in_compete=True)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    @admin.display(description=_('Снять флаг "цена в конкуренции"'))
    def unset_price_in_compete(self, request, queryset):
        result = queryset.filter(price_in_compete=True).update(price_in_compete=False)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    @admin.display(description=_('Mark as bestseller'))
    def set_is_hit(self, request, queryset):
        result = queryset.filter(is_hit=False).update(is_hit=True)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    @admin.display(description=_('Unmark is bestseller'))
    def unset_is_hit(self, request, queryset):
        result = queryset.filter(is_hit=True).update(is_hit=False)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    @admin.display(description='Пометить, как "новый"')
    def set_is_new(self, request, queryset):
        result = queryset.filter(is_new=False).update(is_new=True)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    @admin.display(description='Убрать метку "новый"')
    def unset_is_new(self, request, queryset):
        result = queryset.filter(is_new=True).update(is_new=False)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    @admin.display(description='Добавить признак "расспродажа"')
    def set_is_sale(self, request, queryset):
        result = queryset.filter(is_sale=False).update(is_sale=True)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    @admin.display(description='Убрать признак "расспродажа"')
    def unset_is_sale(self, request, queryset):
        result = queryset.filter(is_sale=True).update(is_sale=False)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    @admin.display(description='Добавить признак "уценка"')
    def set_as_discounted(self, request, queryset):
        result = queryset.filter(discounted=False).update(discounted=True)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    @admin.display(description='Убрать метку "уценка"')
    def unset_as_discounted(self, request, queryset):
        result = queryset.filter(discounted=True).update(discounted=False)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    @admin.display(description='Добавить признак "акция"')
    def set_is_action(self, request, queryset):
        result = queryset.filter(is_action=False).update(is_action=True)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    @admin.display(description='Убрать признак "акция"')
    def unset_is_action(self, request, queryset):
        result = queryset.filter(is_action=True).update(is_action=False)
        self.message_user(request, _('Updated %(result)s objects') % {'result': result})

    def price_update_from_feed(self, request):
        form = PriceFromFeedUpdForm(request.POST or None)
        if request.method == 'POST':
            if form.is_valid():
                result_dict = update_prices_from_feed(
                    url=form.cleaned_data['url'], sku_field=form.cleaned_data['sku']
                )
                if result_dict:
                    for msg in result_dict.get('INFO', []):
                        self.message_user(request, msg, 'INFO')
                    for msg in result_dict.get('ERROR', []):
                        self.message_user(request, msg, 'ERROR')

            return HttpResponseRedirect(reverse('admin:catalog_product_changelist'))

        context = {'form': form}
        return render(request, 'catalog/admin/price_update_from_feed.html', context)

    def vk_sync_all(self, request):
        if 'stroykerbox.apps.vk_market' in settings.INSTALLED_APPS:
            from stroykerbox.apps.vk_market.tasks import run_vk_sync_manually

            output_msg = _(
                'Синхронизация запущена в фоновом режиме. '
                'Результаты можно посмотреть на '
                '<a href="/admin/django_rq/queue/">странице задач в панели администратора</a>.'
            )
            run_vk_sync_manually.delay()
            self.message_user(request, mark_safe(output_msg), 'INFO')
        else:
            self.message_user(request, 'VK-Market is disabled', 'ERROR')
        return HttpResponseRedirect(reverse('admin:catalog_product_changelist'))

    def vk_sync_product(self, request, product_id):
        if 'stroykerbox.apps.vk_market' in settings.INSTALLED_APPS:
            output = call_command('vk_sync', product_id)
            if output:
                self.message_user(request, output, 'INFO')
        else:
            self.message_user(request, 'VK-Market is disabled', 'ERROR')
        return HttpResponseRedirect(
            reverse('admin:catalog_product_change', args=[product_id])
        )

    def props_import(self, request):
        if request.method == 'POST':
            form = ProductPropsImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['file']
                rewrite_props = form.cleaned_data['rewrite_props']
                result_dict = product_props_import(file, rewrite_props)
                if result_dict:
                    for level_str in result_dict.keys():
                        for msg in result_dict[level_str]:
                            self.message_user(
                                request, msg, getattr(messages, level_str, 'INFO')
                            )
                    return HttpResponseRedirect(
                        reverse('admin:catalog_product_changelist')
                    )
        form = ProductPropsImportForm()
        context = {'form': form}
        return render(request, 'catalog/admin/product_props_import.html', context)

    def get_export_queryset(self, request):
        """
        Returns export queryset.

        Default implementation respects applied search and filters.
        """
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        list_select_related = self.get_list_select_related(request)
        list_filter = self.get_list_filter(request)
        search_fields = self.get_search_fields(request)
        if self.get_actions(request):
            list_display = ["action_checkbox"] + list(list_display)

        ChangeList = self.get_changelist(request)
        changelist_kwargs = {
            'request': request,
            'model': self.model,
            'list_display': list_display,
            'list_display_links': list_display_links,
            'list_filter': list_filter,
            'date_hierarchy': self.date_hierarchy,
            'search_fields': search_fields,
            'list_select_related': list_select_related,
            'list_per_page': self.list_per_page,
            'list_max_show_all': self.list_max_show_all,
            'list_editable': self.list_editable,
            'model_admin': self,
        }
        changelist_kwargs['sortable_by'] = self.sortable_by
        if django.VERSION >= (4, 0):
            changelist_kwargs['search_help_text'] = self.search_help_text
        cl = ChangeList(**changelist_kwargs)

        return cl.get_queryset(request)

    def props_export(self, request):
        qs = self.get_export_queryset(request)
        data = product_props_export(qs, 'xls')
        filename = f'product_props_export_{now().strftime("%Y-%m-%d")}.xls'

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename={filename}'
        response.write(data)
        return response

    def images_import(self, request):
        if request.method == 'POST':
            form = ProductImagesImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['file']
                has_headers = form.cleaned_data['has_headers']
                rewrite_images = form.cleaned_data['rewrite_images']
                extension = form.cleaned_data.get('extension')

                resize_width = form.cleaned_data.get('resize_width')
                if resize_width and not isinstance(resize_width, int):
                    resize_width = None

                result_dict = product_images_import(
                    file,
                    has_headers,
                    rewrite_images,
                    resize_width,
                    extension_default=extension,
                )

                if result_dict:
                    levels = {
                        level_str: getattr(messages, level_str)
                        for level_str in result_dict.keys()
                    }
                    messages_count = 100
                    [
                        self.message_user(request, msg, levels[level_str])
                        for level_str, list_msg in result_dict.items()
                        for msg in list_msg[:messages_count]
                    ]
                    skip_messages = 0
                    for level_str, list_msg in result_dict.items():
                        diff = len(list_msg) - messages_count
                        if diff > 0:
                            skip_messages += diff
                    if skip_messages > 0:
                        self.message_user(
                            request, f'Пропущено сообщений: {skip_messages}', 'INFO'
                        )
                    return HttpResponseRedirect(
                        reverse('admin:catalog_product_changelist')
                    )
        form = ProductImagesImportForm()
        context = {'form': form}
        return render(request, 'catalog/admin/product_images_import.html', context)

    def update_search_index(self, request):
        call_command('update_search_index', '--products', verbosity=0)
        self.message_user(
            request, _('The search index for products was successfully updated.')
        )
        return HttpResponseRedirect(reverse('admin:catalog_product_changelist'))

    def apply_watermarks(self, request):
        if not all([config.WATERMARK_PRODUCT_IMAGES, config.WATERMARK_FILE]):
            self.message_user(
                request,
                _(
                    'Watermarking is disabled by the current settings or no watermark file is specified.'
                ),
            )

        watermarked = errors = total = missing = 0

        for img in models.ProductImage.objects.filter(has_watermarked=False):
            total += 1
            try:
                if create_watermark(
                    img.image.path, f'{settings.MEDIA_ROOT}/{config.WATERMARK_FILE}'
                ):
                    img.has_watermarked = True
                    img.save(update_fields=('has_watermarked',))
                    watermarked += 1
            except UnidentifiedImageError:
                missing += 1
                continue
            except Exception:
                errors += 1
                continue

        self.message_user(
            request,
            _(
                'Total processed: %(total)s. '
                'Successfully processed: %(watermarked)s. '
                'Missing images: %(missing)s. '
                'Other errors: %(errors)s'
            )
            % {
                'watermarked': watermarked,
                'errors': errors,
                'total': total,
                'missing': missing,
            },
        )

        if watermarked:
            call_command('thumbnail', 'clear_delete_referenced', verbosity=0)

        return HttpResponseRedirect(reverse('admin:catalog_product_changelist'))

    def product_clone(self, request, product_pk):
        return self.add_clone_view(request, product_pk=product_pk)

    def add_clone_view(self, request, product_pk, deep_clone=True, silence=False):
        if product_pk:
            try:
                original_pk = product_pk
                product = models.Product.objects.get(pk=product_pk)
                categories = product.categories.all()
                product.pk = None
                hex = uuid.uuid4().hex[:8]
                product.name = f'{product.name}-clone-{hex}'
                product.sku = f'{product.sku}-clone-{hex}'
                product.slug = f'{product.slug}-clone-{hex}'
                product.published = False
                last_position = (
                    models.Product.objects.all().order_by('position').last().position
                )
                product.position = last_position + 1
                product.save()
                product.categories.add(*categories)

                product_pk = clone_pk = product.pk

                allready_exists_msg = _(
                    'An error occurred while creating a copy of the product. '
                    'Perhaps a copy of the product with the same name '
                    'already exists, and then you need to rename it.'
                )
                if deep_clone:
                    related_saved = self.clone_product_related(original_pk, clone_pk)
                    if not related_saved:
                        raise ValidationError(allready_exists_msg)
                if not silence:
                    msg = _(
                        'A copy of product {product} has been created. '
                        'If you created this copy by mistake, you must delete it.'.format(
                            product=product.name
                        )
                    )
                    messages.add_message(request, messages.INFO, msg)
            except models.Product.DoesNotExist:
                pass
            except IntegrityError:
                if not silence:
                    raise ValidationError(allready_exists_msg)
                else:
                    pass
            except ValidationError as e:
                messages.add_message(request, messages.ERROR, e)
        return HttpResponseRedirect(f'/admin/catalog/product/{product_pk}/change/')

    @staticmethod
    def clone_product_related(original_pk, clone_pk):
        def make_clone(items, clone, product_field='product'):
            for item in items:
                item.pk = None
                if hasattr(item, product_field):
                    setattr(item, product_field, clone)
                item.save()

        try:
            original = models.Product.objects.get(pk=original_pk)
            clone = models.Product.objects.get(pk=clone_pk)
            # models.ProductParameterValueMembership
            for ppvm in original.params.all():
                param_values = ppvm.parameter_value.all()
                ppvm.pk = None
                ppvm.product = clone
                ppvm.save()
                if param_values:
                    ppvm.parameter_value.add(*list(param_values))
            # models.ProductProps
            make_clone(original.props.iterator(), clone)
            # models.ProductImage
            make_clone(original.images.iterator(), clone)
            # ProductCertificate
            make_clone(original.certificates.iterator(), clone)
            # models.ProductRelated
            make_clone(original.ref.iterator(), clone, 'ref')
            return True
        except models.Product.DoesNotExist:
            return False


@admin.register(models.ProductParameterValueMembership)
class ProductParameterValueMembershipAdmin(admin.ModelAdmin):
    list_display = ('product', 'parameter', 'param_values')
    list_filter = ('product__categories',)
    change_list_template = (
        "catalog/admin/productparametervaluemembership_changelist.html"
    )
    search_fields = (
        'product__sku',
        'product__name',
        'parameter__name',
        'parameter_value__value_str',
    )

    def param_values(self, obj):
        if obj.parameter.data_type == 'decimal':
            return obj.value_decimal
        return ', '.join(obj.parameter_value.values_list('value_str', flat=True)) or ''

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'parametervaluemembership_export',
                self.parametervaluemembership_export,
                name='productparametervaluemembership_export',
            ),
            path(
                'parametervaluemembership_import/',
                self.parametervaluemembership_import,
                name='productparametervaluemembership_import',
            ),
        ]
        return custom_urls + urls

    def get_export_queryset(self, request):
        """
        Returns export queryset.

        Default implementation respects applied search and filters.
        """
        list_display = self.get_list_display(request)
        list_display_links = self.get_list_display_links(request, list_display)
        list_select_related = self.get_list_select_related(request)
        list_filter = self.get_list_filter(request)
        search_fields = self.get_search_fields(request)
        if self.get_actions(request):
            list_display = ["action_checkbox"] + list(list_display)

        ChangeList = self.get_changelist(request)
        changelist_kwargs = {
            'request': request,
            'model': self.model,
            'list_display': list_display,
            'list_display_links': list_display_links,
            'list_filter': list_filter,
            'date_hierarchy': self.date_hierarchy,
            'search_fields': search_fields,
            'list_select_related': list_select_related,
            'list_per_page': self.list_per_page,
            'list_max_show_all': self.list_max_show_all,
            'list_editable': self.list_editable,
            'model_admin': self,
        }
        changelist_kwargs['sortable_by'] = self.sortable_by
        if django.VERSION >= (4, 0):
            changelist_kwargs['search_help_text'] = self.search_help_text
        cl = ChangeList(**changelist_kwargs)

        return cl.get_queryset(request)

    def parametervaluemembership_export(self, request):
        form = ExportBaseForm(request.POST or None)

        if request.method == 'POST':
            if form.is_valid():
                output_format = form.cleaned_data['output_format']
                qs = self.get_export_queryset(request)
                data = productparametervaluemembership_export(qs, output_format)
                filename = f'productparametervalue_export_{now().strftime("%Y-%m-%d")}.{output_format}'

                response = HttpResponse(
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename={filename}'
                response.write(data)
            return response

        context = {'form': form}
        return render(
            request,
            'catalog/admin/productparametervaluemembership_export.html',
            context,
        )

    def parametervaluemembership_import(self, request):
        if request.method == 'POST':
            form = ProductParameterValueImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['file']
                delete_before = form.cleaned_data.get('delete_before')
                result_dict = productparametervaluemembership_import(
                    file, delete_before
                )
                if result_dict:
                    for level_str in result_dict.keys():
                        for msg in result_dict[level_str]:
                            self.message_user(
                                request,
                                mark_safe(msg),
                                getattr(messages, level_str, 'INFO'),
                            )
                    return HttpResponseRedirect(
                        reverse(
                            'admin:catalog_productparametervaluemembership_changelist'
                        )
                    )
        form = ProductParameterValueImportForm()
        context = {'form': form}
        return render(
            request,
            'catalog/admin/productparametervaluemembership_import.html',
            context,
        )


@admin.register(models.ProductAvailabilityStatus)
class ProductAvailabilityStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'range_from', 'range_to')


@admin.register(models.Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'address',
        'third_party_code',
        'pickup_point',
        'position',
    )
    list_display_links = ('name',)
    list_editable = ('position',)


@admin.register(models.ProductLocationPrice)
class ProductLocationPriceAdmin(ImportExportModelAdmin):
    resource_class = resources.ProductLocationPriceResource
    list_display = ('location', 'product', 'price', 'old_price', 'purchase_price')


@admin.register(models.ProductStockAvailability)
class ProductStockAvailabilityAdmin(ImportExportModelAdmin):
    resource_class = resources.ProductStockAvailabilityResource
    list_display = ('stock_name', 'product_sku', 'available')
    list_filter = ('warehouse',)

    def product_sku(self, obj):
        return obj.product.sku

    def stock_name(self, obj):
        return obj.warehouse.name


class ProductSetMembershipInline(admin.TabularInline):
    model = models.ProductSetMembership
    autocomplete_fields = ['product']
    extra = 0
    sortable_field_name = 'position'
    ordering = ('position',)


@admin.register(models.ProductSet)
class ProductSetAdmin(admin.ModelAdmin):
    inlines = (ProductSetMembershipInline,)
    prepopulated_fields = {'key': ('title',)}

    def get_prepopulated_fields(self, request, obj=None):
        if not obj:
            return self.prepopulated_fields
        return {}

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('key',)
        return super().get_readonly_fields(request, obj)


@admin.register(models.MoySkladSyncLog)
class MoySkladSyncLogAdmin(admin.ModelAdmin):
    list_display = ('operation', 'start_dt', 'summary')


@admin.register(models.ProductPriceHistory)
class ProductPriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('product', 'price', 'created', 'location')


@admin.register(models.Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'is_default')

    def has_delete_permission(self, request, obj=None):
        return not getattr(obj, 'is_default', False)


class YmlCustomProductExportInline(admin.TabularInline):
    autocomplete_fields = ['product']
    extra = 0
    model = models.YmlCustomProductExport


class YmlCustomExportAdminForm(forms.ModelForm):
    class Meta:
        model = models.YmlCustomExport
        exclude = []

    def clean(self):
        if self.cleaned_data['type'] == models.YmlCustomExport.CATEGORY:
            if not self.cleaned_data['categories']:
                raise ValidationError(
                    'Выбран тип: "Категория", но не указано ни одной категории.'
                )
        return self.cleaned_data


@admin.register(models.YmlCustomExport)
class YmlCustomExportAdmin(admin.ModelAdmin):
    form = YmlCustomExportAdminForm
    inlines = [YmlCustomProductExportInline]
    actions = ['run_export']

    def run_export(self, request, queryset):
        for yml_export in queryset:
            call_command('export_to_yml_custom', slug=yml_export.slug)
        self.message_user(request, _('Файлы сформированы'), messages.SUCCESS)

    run_export.short_description = _('Выполнить экспорт')


class RelatedProductsFilter(MultipleChoiceListFilter):
    title = _('Категории')
    parameter_name = 'categories__in'

    def lookups(self, request, model_admin):
        return models.Category.objects.values_list('pk', 'name')


class RelProductCategoryListFilter(MultipleChoiceListFilter):
    title = _('Категории')
    parameter_name = 'ref__categories__in'

    def lookups(self, request, model_admin):
        return models.Category.objects.values_list('pk', 'name')


@admin.register(models.ProductRelated)
class ProductRelatedAdmin(ImportExportModelAdmin):
    list_display = ('ref_sku', 'product_sku', 'position')
    list_filter = (RelProductCategoryListFilter,)
    search_fields = ('ref__sku', 'ref__name')
    autocomplete_fields = ('ref', 'product')
    resource_class = resources.ProductRelatedResource

    def ref_sku(self, obj):
        if obj:
            return obj.ref.sku
        return ''

    def product_sku(self, obj):
        if obj:
            return obj.product.sku
        return ''
