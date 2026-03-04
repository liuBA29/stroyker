from typing import Optional, Any
import importlib
import re

from stroykerbox.apps.locations.models import Location


def string_to_int(string: str) -> int:
    if isinstance(string, str):
        try:
            return int(re.sub(r'\D', '', string))
        except Exception:
            pass
    return 0


def clear_punctuation(string: str) -> str:
    if isinstance(string, str):
        return re.sub(r'[^\w\s]', ' ', string.replace('-', ' '))
    return string


def get_site_phones(location: Optional[Any] = None, *args, **kwargs) -> list[Any]:
    if not location:
        location = Location.get_default_location()

    if isinstance(location, Location):
        try:
            return location.phones.values('phone', 'phone_raw')
        except AttributeError:
            pass
    return []


def clear_phone(input_phone: str, country_code: int = 7) -> str:
    phone = re.sub(r'\D', '', str(input_phone))
    if len(phone) >= 10:
        return f'{country_code or ""}{phone[-10:]}'
    return phone


def import_function(path):
    """
    Given the fully qualified path to the function, return that function.
    """
    # path should be of the form module.submodule...submodule.function
    # function name is the element after the last period
    function_name = path.split('.')[-1]
    # the module path is the full path minus the function_name and its leading
    # period.
    module_path = path[: -len(function_name) - 1]
    lib = importlib.import_module(module_path)
    return lib.__getattribute__(function_name)


def clear_scheduled_jobs(scheduler, logger):
    # Delete any existing jobs in the scheduler when the app starts up
    for job in scheduler.get_jobs():
        logger.debug("Deleting scheduled job %s", job)
        job.delete()
