from typing import Optional

from django.views.generic.list import ListView
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.db.models import QuerySet
from django_geoip.base import storage_class

from constance import config
from stroykerbox.apps.locations.models import Location
from stroykerbox.apps.statictext.models import Statictext

from .models import Partner, Contact, PartnerCategory, PartnerCity

NEW_PARTNER_BTN_STATICTEXT_KEY = 'partners_new_partner_btn'


class AddressViewCommonMixin:
    def setup(self, request, *args, **kwargs):
        self.locations = Location.get_available_locations()
        self.location = None

        slug = request.GET.get('location')
        if slug:
            self.location = get_object_or_404(Location, slug=slug)
        elif request.location and request.location.is_active:
            self.location = request.location
        else:
            self.location = Location.get_default_location()

        super().setup(request, *args, **kwargs)  # type: ignore

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)  # type: ignore

        context['center_latitude'] = (
            self.location.center_latitude
            if self.location
            else config.YAMAP_DEFAULT_CENTER_LATITUDE
        )
        context['center_longitude'] = (
            self.location.center_longitude
            if self.location
            else config.YAMAP_DEFAULT_CENTER_LONGITUDE
        )

        context['center_zoom'] = config.YAMAP_DEFAULT_CENTER_ZOOM
        context['current_location'] = self.location
        context['use_glyph'] = (
            self.get_queryset().filter(ymap_glyph_icon__isnull=False).exists()  # type: ignore
        )
        return context


class PartnerLocationListView(AddressViewCommonMixin, ListView):
    """
    A page with a list of all active partners in the specific location.
    """

    context_object_name = 'addresses'
    template_name = 'addresses/partner-list.html'
    queryset = Partner.objects.filter(is_active=True)

    def get_queryset(self):
        filter = {}

        if category_slug := self.request.GET.get('category'):
            filter['category__slug'] = category_slug

        # https://redmine.nastroyker.ru/issues/16738#change-89523
        if city_slug := self.request.GET.get('city'):
            filter['city__slug'] = city_slug

        if self.location:
            filter['location_id'] = self.location.id
        else:
            filter['location__isnull'] = True
        return self.queryset.filter(**filter)

    def get_partner_categories_data(self) -> Optional[QuerySet]:
        qs = PartnerCategory.objects.filter(partners__is_active=True)
        if self.location:
            qs = qs.filter(partners__location=self.location)

        partner_categories = qs.distinct()

        if partner_categories.count() > 1:
            return partner_categories

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['locations'] = self.locations.exclude(partners__isnull=True)
        context['partner_categories'] = self.get_partner_categories_data()
        context['partner_cities'] = PartnerCity.objects.filter(
            partners__isnull=False
        ).distinct()

        # https://redmine.nastroyker.ru/issues/17193
        try:
            new_partner_btn = Statictext.objects.filter(
                key=NEW_PARTNER_BTN_STATICTEXT_KEY
            ).first()
        except Statictext.DoesNotExist:
            pass
        else:
            context['new_partner_btn'] = new_partner_btn.text

        if self.location and hasattr(self.request, 'seo'):
            title = _('Partners in location "%(location)s"') % {
                'location': self.location.city
            }

            # https://redmine.nastroyker.ru/issues/16738#change-89523
            breadcrumb_title = 'Партнеры'

            self.request.seo.breadcrumbs.append((self.request.path, breadcrumb_title))
            self.request.seo.title.append(title)

        return context


class ContactsPageView(AddressViewCommonMixin, ListView):
    """
    A page with a list of all active contact items.
    From all locations.
    """

    context_object_name = 'addresses'
    template_name = 'addresses/contacts-page.html'

    def render_to_response(self, context, **response_kwargs):
        # https://redmine.fancymedia.ru/issues/12756
        response = super().render_to_response(context, **response_kwargs)
        location_slug = self.request.GET.get('location')
        if location_slug:
            try:
                location = Location.objects.get(slug=location_slug)
            except Location.DoesNotExist:
                pass
            else:
                response = HttpResponseRedirect(self.request.path)
                storage_class(request=self.request, response=response).set(
                    location=location, force=True
                )

        return response

    def get_queryset(self):
        qs = Contact.objects.filter(is_active=True)
        if self.location:
            qs = qs.filter(location=self.location)
        return qs

    def get_available_locations(self):
        available_locations_qs = (
            Contact.objects.filter(is_active=True)
            .order_by('location__position', 'location__pk')
            .only('location')
        )
        available_locations = []

        for i in available_locations_qs:
            if i.location not in available_locations:
                available_locations.append(i.location)
        return available_locations

    def get_context_data(self, **kwargs):
        if hasattr(self.request, 'seo'):
            title = _('Contacts')
            self.request.seo.breadcrumbs.append((reverse('contacts-page'), title))
            self.request.seo.title.append(title)
        context = super().get_context_data(**kwargs)

        available_locations = self.get_available_locations()

        if len(available_locations) > 1:
            context['locations'] = available_locations
        return context
