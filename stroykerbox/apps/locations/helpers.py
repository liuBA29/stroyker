from django.db.models import Manager, Q


class LocationModelManager(Manager):
    def for_location(self, location=None):
        if location:
            query = Q(location=location)
            if location.is_default:
                query |= Q(location__isnull=True)
            return self.filter(query)
        return self.filter(location__isnull=True)
