from django import forms
from django.shortcuts import render, redirect
from django.contrib import admin
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.utils.translation import ugettext as _

from .models import Category


class SetCategoriesForm(forms.Form):
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    delete_exists = forms.BooleanField(
        label='', required=False,
        help_text=_('Удалять текущие категории перед назначением новых.'))
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(), label=_('Категории для назначения'))


@admin.display(description=_('Назначить категории'))
def set_categories(modeladmin, request, queryset):
    form = None

    if 'apply' in request.POST:
        form = SetCategoriesForm(request.POST)

        if form.is_valid():
            categories = form.cleaned_data['categories']
            delete_exists = form.cleaned_data['delete_exists']

            count = 0
            for item in queryset:
                if delete_exists:
                    item.categories.clear()
                item.categories.add(*categories)
                count += 1

            msg = _('Назначены категории для %(count)s товаров') % {
                'count': count}
            modeladmin.message_user(
                request, msg)
            return redirect(request.get_full_path())

    if not form:
        form = SetCategoriesForm(
            initial={'_selected_action': request.POST.getlist(ACTION_CHECKBOX_NAME)})

    return render(request, 'catalog/admin/set-categories.html', {
        'items': queryset,
        'form': form,
        'title': _('Назначение категорий для товаров каталога')
    })
