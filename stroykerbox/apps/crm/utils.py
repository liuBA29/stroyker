from django.apps import apps as django_apps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_order_model():
    """
    Returns the Order model that is active in this project.
    Works like the get_user_model function from the Django core.
    """
    try:
        return django_apps.get_model(settings.ORDER_MODEL, require_ready=False)
    except ValueError:
        raise ImproperlyConfigured(
            "ORDER_MODEL must be of the form 'app_label.model_name'")
    except LookupError:
        raise ImproperlyConfigured(
            "ORDER_MODEL refers to model '%s' that has not been installed" % settings.ORDER_MODEL
        )
