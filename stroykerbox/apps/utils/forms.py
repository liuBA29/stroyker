from typing import Optional

from django import forms
from django.db.models import Count
from django.forms import BoundField
from django.utils.safestring import mark_safe
from django.utils.text import slugify as django_slugify
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Invisible
from slugify import slugify
from constance import config

from stroykerbox.apps.catalog.models import ProductStockAvailability
from stroykerbox.apps.catalog.widgets import MultiChoiceFilterWidget
from stroykerbox.apps.ycaptcha.fields import YandexCaptchaField
from stroykerbox.apps.ycaptcha.widgets import YandexCaptchaWidget
from stroykerbox.settings.constants import CAPTCHA_MODE_YANDEX, CAPTCHA_MODE_GOOGLE
from .widgets import SlugPreviewWidget
from .validators import ValidateSlug


class ReCaptchaFormMixin:

    # Название JS-функции, которая будет вызвана через ReCaptcha при отправке формы.
    # Если не указана (отсутствует), тогда форма будет отправляться стандартным
    # образом, не зависимо от навешанных на нее обработчиков события отправки (js)
    # - они все будут отменены в скрипте recaptch`и.
    # Должно быть переопределено для каждой формы, где нужна какая-либо нестандартная
    # обработка отправки.
    SUBMIT_CALLBACK: Optional[str] = None

    def captcha_enabled(self) -> bool:
        if config.CAPTCHA_MODE == CAPTCHA_MODE_YANDEX:
            return all((config.YCAPTCHA_SERVER_KEY, config.YCAPTCHA_CLIENT_KEY))
        elif config.CAPTCHA_MODE == CAPTCHA_MODE_GOOGLE:
            return all((config.RECAPTCHA_PRIVATE_KEY, config.RECAPTCHA_PUBLIC_KEY))
        return False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.captcha_enabled():
            if config.CAPTCHA_MODE == CAPTCHA_MODE_YANDEX:
                self.fields['captcha'] = YandexCaptchaField(  # type: ignore
                    widget=YandexCaptchaWidget(submit_callback=self.SUBMIT_CALLBACK)
                )
            else:
                attrs = {'id': f'cap-{self.__class__.__name__.lower()}'}
                if self.SUBMIT_CALLBACK:
                    attrs['data-callback'] = self.SUBMIT_CALLBACK
                self.fields['captcha'] = ReCaptchaField(  # type: ignore
                    public_key=config.RECAPTCHA_PUBLIC_KEY,
                    private_key=config.RECAPTCHA_PRIVATE_KEY,
                    widget=ReCaptchaV2Invisible(attrs=attrs),
                )


class StockFilterForm(forms.Form):
    stock = forms.ModelMultipleChoiceField(
        queryset=None, required=None, widget=MultiChoiceFilterWidget
    )

    def __init__(self, products=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        qs = ProductStockAvailability.objects.values('warehouse')

        if products:
            qs = qs.filter(product_id__in=products)

        warehouse_label_field = f'warehouse__{config.CATALOG_STOCK_FILTER_NAME_FIELD}'
        qs = qs.annotate(products_count=Count('product')).values(
            'warehouse__id',
            f'{warehouse_label_field}',
            'warehouse__address',
            'products_count',
        )

        self.fields['stock'].choices = [
            (
                s['warehouse__id'],
                mark_safe(
                    s[f'{warehouse_label_field}']
                    + f' <span>{s["products_count"]}</span>'
                ),
            )
            for s in qs
        ]


class SlugPreviewFormMixin:
    """
    Form Mixin to add necessary integration for the SlugPreviewField.
    This extends the default ``form[field]`` interface that produces the BoundField for HTML templates.
    """

    def __getitem__(self, item):
        boundfield = super().__getitem__(item)  # type: ignore
        if isinstance(boundfield.field, SlugPreviewField):
            boundfield.__class__ = _upgrade_boundfield_class(boundfield.__class__)
        return boundfield


class BoundSlugField(BoundField):
    """
    An exta integration to pass information of the form to the widget.
    This is loaded via :class:`SlugPreviewFormMixin`
    """

    def as_widget(self, widget=None, attrs=None, only_initial=False):
        if not widget:
            widget = self.field.widget

        widget.instance = (
            self.form.instance
        )  # Widget needs ability to fill in the blanks.
        return super().as_widget(widget=widget, attrs=attrs, only_initial=only_initial)


UPGRADED_CLASSES = {}


def _upgrade_boundfield_class(cls):
    if cls is BoundField:
        return BoundSlugField
    elif issubclass(cls, BoundSlugField):
        return cls

    # When some other package also performs this same trick,
    # combine both classes on the fly. Avoid having to do that each time.
    # This is needed for django-parler
    try:
        return UPGRADED_CLASSES[cls]
    except KeyError:
        # Create once
        new_cls = type(f"BoundSlugField_{cls.__name__}", (cls, BoundSlugField), {})
        UPGRADED_CLASSES[cls] = new_cls
        return new_cls


class SlugPreviewModelForm(SlugPreviewFormMixin, forms.ModelForm):
    """
    A default model form, configured with the :class:`SlugPreviewFormMixin`.
    """


class SlugPreviewField(forms.SlugField):
    """
    A Form field that displays the slug and preview.
    It requires the :class:`SlugPreviewFormMixin` to be present in the form.
    """

    widget = SlugPreviewWidget

    def __init__(self, *args, **kwargs):
        self.populate_from = kwargs.pop("populate_from", None)
        self.always_update = kwargs.pop("always_update", False)
        self.url_format = kwargs.pop("url_format", None)
        self.slugify = kwargs.pop("slugify", slugify)

        if self.slugify != django_slugify:
            # This replaces the 'default_validators' setting at object level.
            self.default_validators = [ValidateSlug(self.slugify)]

        super().__init__(*args, **kwargs)
        self.widget.url_format = self.url_format

    def widget_attrs(self, widget):
        # Expose the form field settings to HTML
        attrs = super().widget_attrs(widget)
        attrs.update(
            {
                "data-populate-from": self.populate_from,
                "data-url-format": self.url_format,
                "data-always-update": self.always_update,
            }
        )
        return attrs
