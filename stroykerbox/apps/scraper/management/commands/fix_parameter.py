from django.core.management.base import BaseCommand

from stroykerbox.apps.catalog.models import Product, Parameter, ParameterValue, ProductParameterValueMembership


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('category', type=str, help='Category internal slug')
        parser.add_argument('parameter', type=str, help='Parameter internal slug')

    def handle(self, *args, **options):
        category_slug = options.get('category')
        parameter_slug = options.get('parameter')
        products = Product.objects.filter(category__slug=category_slug)
        pvs = ParameterValue.objects.filter(parameter__slug=parameter_slug)
        pvs_names = pvs.values_list('value_str', flat=True)
        mp = Parameter.objects.filter(slug=parameter_slug)[0]
        for p in products:
            params = p.params.values('parameter')
            if mp in params:
                continue
            for pvs_name in pvs_names:
                if pvs_name.upper() in p.name.upper():
                    pv = ParameterValue.objects.filter(value_str=pvs_name)[0]
                    ppvm, _ = ProductParameterValueMembership.objects.get_or_create(product=p, parameter=mp)
                    if pv not in ppvm.parameter_value.all():
                        ppvm.parameter_value.add(pv)
