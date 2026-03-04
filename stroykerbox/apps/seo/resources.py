from import_export import resources

from .models import MetaTag


class MetaTagBaseResource(resources.ModelResource):
    class Meta:
        model = MetaTag
        exclude = []
