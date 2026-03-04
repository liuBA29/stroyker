from datetime import date, timedelta, datetime

from django.shortcuts import redirect, get_object_or_404
from django.views.generic import TemplateView
from django.contrib import messages
from django.http import HttpResponseBadRequest

from .models import ItemSet, Item, ItemReserve
from .forms import BookingForm


class MatrixPage(TemplateView):
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.matrix = get_object_or_404(ItemSet, key=kwargs.get('key'), published=True)
        today = date.today()

        self.custom_date = kwargs.get('custom_date')
        self.current_date = self.custom_date or today
        self.today = today

        self.hours_set = self.matrix.hours_set

    def get_template_names(self):
        if self.hours_set:
            return 'booking/matrix-for-hours.html'
        return 'booking/matrix-for-days.html'

    def get(self, request, *args, **kwargs):
        if hasattr(request, 'seo'):
            request.seo.breadcrumbs.append((None, self.matrix.name))
            request.seo.title.append(self.matrix.name)
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context)

    def get_header_dates(self):
        result = [self.today]
        if self.hours_set:
            for n in range(1, 8):
                result.append(self.today + timedelta(n))
        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['matrix'] = self.matrix
        items = self.matrix.items.all()

        if self.hours_set:
            current_datetime = datetime(
                self.current_date.year, self.current_date.month, self.current_date.day
            )
            context['hours_dates'] = [
                current_datetime.replace(hour=h) for h in self.hours_set
            ]
        else:
            week_dates_list = [self.today]
            for n in range(1, 7):
                week_dates_list.append(self.today + timedelta(n))

            context['week_dates'] = week_dates_list

        context['current_date'] = self.current_date
        context['now'] = datetime.now()
        context['today'] = self.today
        context['items'] = items
        context['header_dates'] = self.get_header_dates()

        return context


def add_reserve(request, itemset_key, item_id, reserve_date, hour=None):
    if request.method != 'POST':
        return HttpResponseBadRequest()

    itemset = get_object_or_404(ItemSet, key=itemset_key)
    redirect_path = request.POST.get('next') or itemset.get_absolute_url(reserve_date)

    form = BookingForm(request.POST)

    if not form.is_valid():
        for err in form.errors.values():
            messages.error(request, err)
        return redirect(redirect_path)

    form_data = form.cleaned_data

    phone = form_data.get('phone')

    if not phone:
        messages.error(request, 'Не указан телефон для связи.')
    else:
        try:
            item = Item.objects.get(itemset=itemset, id=item_id)
        except Item.DoesNotExist:
            messages.error(request, 'Слот не найден.')
        else:
            add_kwargs = dict(
                item=item,
                date=reserve_date,
                hour=hour,
                phone=phone,
                comment=form_data.get('message'),
                name=form_data.get('name'),
            )
            if ItemReserve.objects.filter(**add_kwargs).exists():
                messages.error(request, 'Данный слот на эту дату уже зарезервирован.')
            else:
                reserve = ItemReserve.objects.create(**add_kwargs)
                reserve.create_ahead_slots_reserve()

                if hour:
                    msg = (
                        f'Бронь для слота {reserve.item} на {reserve.date} '
                        f'{reserve.hour}:00 ч. успешно добавлена.'
                    )
                else:
                    msg = f'Бронь для слота {reserve.item} на {reserve.date}s успешно добавлена.'

                messages.success(request, msg)

    return redirect(redirect_path)
