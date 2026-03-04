from datetime import date, datetime

from django import template

from stroykerbox.apps.booking.forms import BookingForm


register = template.Library()


@register.filter
def date_is_past(date_obj):
    if isinstance(date_obj, datetime):
        return date_obj < datetime.now()
    if isinstance(date_obj, date):
        return date_obj < date.today()


@register.filter
def has_reserve(item, date_obj):
    if isinstance(date_obj, datetime):
        return item.reserves.filter(
            date__year=date_obj.year,
            date__month=date_obj.month,
            date__day=date_obj.day,
            hour=date_obj.hour).exists()
    if isinstance(date_obj, date):
        return item.reserves.filter(date=date_obj).exists()


@register.inclusion_tag('booking/tags/booking-form.html', takes_context=True)
def render_booking_form(context):
    context['booking_form'] = BookingForm()
    return context
