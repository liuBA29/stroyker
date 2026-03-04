import importlib
import inspect
import os

from django.apps import apps


def load_tag_library(libname):
    """
    Load a templatetag library on multiple Django versions.

    Returns None if the library isn't loaded.
    """
    from django.template.backends.django import get_installed_libraries
    from django.template.library import InvalidTemplateLibrary
    try:
        lib = get_installed_libraries()[libname]
        return importlib.import_module(lib).register
    except (InvalidTemplateLibrary, KeyError):
        pass


def get_template_tags_full():
    """
    Dictionaries whith all template tags from all custom apps.
    """
    results = {}
    for app_config in apps.get_app_configs():
        app = app_config.name
        app_label = app_config.verbose_name
        if not app.startswith('stroykerbox'):
            continue
        try:
            templatetag_mod = __import__(app + '.templatetags', {}, {}, [''])
        except ImportError:
            continue
        mod_path = inspect.getabsfile(templatetag_mod)
        mod_files = os.listdir(os.path.dirname(mod_path))
        tag_files = [i.rstrip('.py')
                     for i in mod_files if i.endswith('.py') and i[0] != '_']
        app_labeled = False
        for taglib in tag_files:
            lib = load_tag_library(taglib)
            if lib is None:
                continue

            if not app_labeled:
                results[app] = {}
                results[app]['app_label'] = app_label
                results[app][taglib] = []
                app_labeled = True

            for tag in lib.tags:
                try:
                    results[app][taglib].append(tag)
                except KeyError:
                    pass

    return results


def get_slider_template_tags_list():
    """
    A list of template tags from custom apps that contain 'slider' in their name.
    Example for the list item (str):
        'some_tag_lib:tag_name'
    """
    results = []
    for app_config in apps.get_app_configs():
        app = app_config.name

        if not app.startswith('stroykerbox'):
            continue
        try:
            templatetag_mod = __import__(app + '.templatetags', {}, {}, [''])
        except ImportError:
            continue
        mod_path = inspect.getabsfile(templatetag_mod)
        mod_files = os.listdir(os.path.dirname(mod_path))
        tag_files = (i.rstrip('.py') for i in mod_files if i.endswith('.py') and i[0] != '_')

        for taglib in tag_files:

            lib = load_tag_library(taglib)
            if lib is None:
                continue

            for tag in lib.tags:
                if 'render' in tag:
                    tag_line = f'{taglib}:{tag}'
                    results.append((tag_line, tag_line))

    return results
