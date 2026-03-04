from typing import Any
from urllib.parse import quote

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property
from django.utils.html import strip_tags, mark_safe
from django.contrib.sites.models import Site
from django.conf import settings

from stroykerbox.apps.locations.models import Location
from stroykerbox.apps.utils.utils import clear_phone
from stroykerbox.apps.crm.forms import HIDDEN_EXT_FIELDS


FORM_FIELD_CLASS_CHOICES = {
    ('django.forms.CharField', _('text string')),
    ('stroykerbox.apps.custom_forms.fields.TextareaField', _('multiline text')),
    ('stroykerbox.apps.custom_forms.fields.PhoneField', _('phone')),
    ('stroykerbox.apps.custom_forms.fields.FileField', _('multiple files')),
    (
        'stroykerbox.apps.custom_forms.fields.PseudoFileField',
        _('multiple files with preload'),
    ),
    ('django.forms.EmailField', _('email')),
    ('django.forms.URLField', _('url')),
    ('django.forms.BooleanField', _('boolean')),
    ('django.forms.FileField', _('file')),
    ('django.forms.FloatField', _('float')),
    ('django.forms.IntegerField', _('integer')),
    ('stroykerbox.apps.custom_forms.fields.DateField', _('date')),
    ('stroykerbox.apps.custom_forms.fields.SelectField', _('select field')),
}


class CustomSelectFieldModel(models.Model):
    key = models.SlugField(
        _('html name'), help_text=_('Field name from custom forms'), unique=True
    )

    def __str__(self):
        return self.key

    class Meta:
        ordering = (
            'key',
            'pk',
        )
        verbose_name = _('custom select field')
        verbose_name_plural = _('custom select fields')


class CustomSelectFieldChoiceModel(models.Model):
    field = models.ForeignKey(
        CustomSelectFieldModel, related_name='choices', on_delete=models.CASCADE
    )
    value = models.CharField(_('value'), max_length=50)
    position = models.PositiveIntegerField(_('position'), default=0)

    def __str__(self):
        return self.value

    class Meta:
        ordering = (
            'position',
            'value',
        )
        verbose_name = _('custom choice of select field')
        verbose_name_plural = _('custom choices of select field')


class CustomForm(models.Model):
    title = models.CharField(_('title'), max_length=128)
    key = models.SlugField(_('key'), primary_key=True)
    active = models.BooleanField(_('active'), default=True)
    metrica_goal = models.CharField(
        'имя цели для я-метрики', max_length=32, null=True, blank=True
    )
    telegram_chat_id = models.BigIntegerField(
        _('telegram chat_id'),
        null=True,
        blank=True,
        help_text=_(
            'ID чата в Телеграм, куда отправлять уведомления о '
            'заполнениях формы. Если не указано, тогда используется '
            'chat_id из глобальных настроек.'
        ),
    )

    class Meta:
        ordering = ('title',)
        verbose_name = _('custom form')
        verbose_name_plural = _('custom forms')

    def __str__(self):
        return self.title


class CustomFormField(models.Model):
    form = models.ForeignKey(
        CustomForm, on_delete=models.CASCADE, related_name='fields'
    )
    field_class = models.CharField(
        _('form field class'), max_length=128, choices=FORM_FIELD_CLASS_CHOICES
    )
    label = models.CharField(_('field label'), max_length=32)
    show_label = models.BooleanField(_('show label'), default=True)
    html_name = models.SlugField(
        _('html name'), help_text=_('Field name for html form.')
    )
    placeholder = models.CharField(
        _('field placeholder'), max_length=64, null=True, blank=True
    )
    css_classes = models.CharField(
        _('css classes'),
        max_length=256,
        null=True,
        blank=True,
        help_text=_('CSS class(es) for the field. Separate by space.'),
    )
    required = models.BooleanField(_('field is required'), default=True)
    position = models.PositiveIntegerField(_('position'), default=0)
    b24_alias = models.CharField(
        'поле в b24',
        max_length=32,
        null=True,
        blank=True,
        choices=[(f, f) for f in ('NAME', 'PHONE', 'EMAIL', 'COMMENTS')],
        help_text='Альяс(сопоставление) поля для Bitrix24',
    )

    class Meta:
        verbose_name = _('custom form field')
        verbose_name_plural = _('custom form fields')
        ordering = ('position',)

    def __str__(self):
        return self.label


class CustomFormResult(models.Model):
    form = models.ForeignKey(CustomForm, on_delete=models.CASCADE)
    results = models.JSONField(_('results'), default=dict)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    location = models.ForeignKey(
        Location, null=True, blank=True, on_delete=models.SET_NULL
    )
    page_url = models.URLField(
        _('url страницы отправки'),
        null=True,
        blank=True,
        help_text=_('URL страницы, с которой была отправлена форма.'),
    )

    class Meta:
        ordering = ('-created',)
        verbose_name = _('custom form result')
        verbose_name_plural = _('custom form results')

    def __str__(self):
        return f'results for {self.form.title}'

    def get_b24_comments(self):
        output = []
        for f in self.form.fields.filter(b24_alias='COMMENTS'):
            value = self.results.get(f.html_name)
            if value:
                output.append(f'{f.label}:{value}')
        output.append(self.page_url)
        return ';'.join(output)

    def get_b24_field_value(self, b24_field_name):
        field = self.form.fields.filter(b24_alias=b24_field_name).last()
        if field:
            return self.results.get(field.html_name)

    @property
    def b24_utm(self):
        # https://redmine.fancymedia.ru/issues/12839
        output = {}
        for key, fieldname in HIDDEN_EXT_FIELDS.items():
            if key == 'PAGE_URL_FIELDNAME' or not self.results.get(fieldname):
                continue
            output[fieldname.upper()] = self.results[fieldname]
        return output

    @property
    def b24_fields(self):
        site = Site.objects.get_current()

        fields_dict = {
            'TITLE': _('Request by form "%(form_name)s" from site %(site)s')
            % {'form_name': self.form.title, 'site': site.domain},
            'COMMENTS': self.get_b24_comments(),
            'SOURCE_DESCRIPTION': self.form.title.capitalize(),
        }

        name = self.get_b24_field_value('NAME')
        if name:
            fields_dict['NAME'] = name

        phone = self.get_b24_field_value('PHONE')
        if phone:
            fields_dict['PHONE'] = [{'VALUE': phone, 'VALUE_TYPE': 'WORK'}]

        email = self.get_b24_field_value('EMAIL')
        if email:
            fields_dict['EMAIL'] = [{'VALUE': email, 'VALUE_TYPE': 'WORK'}]

        # https://redmine.fancymedia.ru/issues/12839
        fields_dict.update(self.b24_utm)

        return fields_dict

    @cached_property
    def has_files(self):
        return self.form.fields.filter(field_class__endswith='FileField').exists()

    @property
    def result_strings_dict(self) -> dict[str, str]:
        result = {}
        qs = self.form.fields.values('html_name', 'label', 'field_class').exclude(
            field_class__endswith='FileField'
        )
        for field in qs:
            value = strip_tags(self.results[field['html_name']])
            if field['field_class'].endswith('PhoneField'):
                value = clear_phone(value)
                value = mark_safe(f'<a href="tel:+{value}">+{value}</a>')
            elif field['field_class'].endswith('EmailField'):
                value = mark_safe(f'<a href="mailto:{value}">{value}</a>')
            result[field['label']] = value
        return result

    @property
    def result_files_dict(self) -> dict[str, Any]:
        result = {}

        media_url = settings.MEDIA_URL.rstrip('/')
        base_url = f'http://{Site.objects.get_current().domain}'
        init_url = f'http://{base_url}{media_url}'

        qs = self.form.fields.filter(field_class__endswith='FileField').values(
            'html_name', 'label', 'field_class'
        )

        for field in qs:
            value = self.results[field['html_name']]
            if isinstance(value, list):
                urls = []
                for url in value:
                    if url.startswith(media_url):
                        urls.append(base_url + quote(url))
                    else:
                        urls.append(init_url + quote(url))

                result[field['label']] = urls
            else:
                result[field['label']] = init_url + quote(value)  # type: ignore
        return result

    def to_dict(self) -> dict[str, str]:
        output = {'Форма': self.form.title}
        output.update(self.result_strings_dict)
        output.update(self.result_strings_dict)
        return output
