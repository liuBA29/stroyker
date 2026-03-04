from collections import defaultdict

from django.db.models import Q
from django.core.files.uploadedfile import InMemoryUploadedFile
from import_export import resources
from import_export.fields import Field
from import_export.widgets import ManyToManyWidget
from import_export.widgets import ForeignKeyWidget
import tablib

from stroykerbox.apps.locations.models import Location

from .models import Partner, PartnerCoordinates, PartnerCategory, PartnerCity


IMPORT_EXPORT_FIELDS = (
    'id',
    'name',
    'address',
    'location',
    'phone',
    'email',
    'description',
    'website',
    'page_url',
    'category',
    'coordinates',
    'is_active',
    'position',
)


class PartnerResourceBase(resources.ModelResource):
    coordinates = Field(
        attribute='coordinates',
        column_name='coordinates',
        widget=ManyToManyWidget(PartnerCoordinates, field='coordinates', separator=';'),
    )
    location = Field(
        column_name='location',
        attribute='location',
        widget=ForeignKeyWidget(Location, field='id'),
    )

    category = Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(PartnerCategory, field='id'),
    )

    city = Field(
        column_name='city',
        attribute='city',
        widget=ForeignKeyWidget(PartnerCity, field='id'),
    )

    class Meta:
        model = Partner
        fields = export_order = IMPORT_EXPORT_FIELDS


def partner_import_data(file: InMemoryUploadedFile):
    messages = defaultdict(list)
    skiped = created = updated = 0
    imported_data = tablib.Dataset().load(file)

    for row in imported_data.dict:
        pk = int(row.pop('id', 0) or 0)
        coordinates = [c.strip() for c in row.pop('coordinates', []).split(';')]
        category_id = row.pop('category', None)
        city_id = row.pop('city', None)
        location_id = row.pop('location', None)
        position = row.pop('position', None)

        is_active = row.pop('is_active', None) or 1
        if isinstance(is_active, str):
            try:
                is_active = int(is_active)
            except ValueError:
                is_active = 1

        upd_data = dict(row)

        upd_data['is_active'] = bool(is_active)

        upd_data['category'] = (
            PartnerCategory.objects.filter(id=category_id).first()
            if category_id
            else None
        )

        upd_data['city'] = (
            PartnerCity.objects.filter(id=city_id).first() if city_id else None
        )

        if location_id:
            upd_data['location'] = Location.objects.filter(id=location_id).first()

        upd_data['position'] = position or 0

        if pk:
            try:
                Partner.objects.filter(pk=pk).update(**upd_data)
            except Exception as e:
                messages['ERROR'].append(str(e))
                skiped += 1
                continue
            else:
                updated += 1

                if coordinates:
                    PartnerCoordinates.objects.filter(
                        Q(partner_id=pk) & ~Q(coordinates__in=coordinates)
                    ).delete()
        else:
            try:
                obj = Partner.objects.create(**upd_data)
                pk = obj.pk
            except Exception as e:
                messages['ERROR'].append(str(e))
                skiped += 1
                continue
            else:
                created += 1

        for coord in coordinates:
            if not coord:
                continue
            if not PartnerCoordinates.objects.filter(
                partner_id=pk, coordinates__contains=coord
            ).exists():
                PartnerCoordinates.objects.create(partner_id=pk, coordinates=coord)
                updated += 1

    messages['INFO'].append(
        f'Новых партнеров: {created}' f'\nПропущено: {skiped}' f'\nОбновлено: {updated}'
    )
    return messages
