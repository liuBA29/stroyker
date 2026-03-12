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


# Контейнеры «Новый дизайн: блоки главной страницы» и «Новый дизайн: блоки футера»
# показывают только эти теги в выпадающем списке (см. admin SliderTagContainerItemInline).
# Для заказчика везде используем префикс new_design (не 8march): имена тегов и подписи в админке.
NEW_DESIGN_TAG_LINES = [
    ('customization_tags:render_new_design_hero_block', 'new_design: герой (карусель)'),
    ('customization_tags:render_new_design_actions_block', 'new_design: акции'),
    ('customization_tags:render_new_design_bouquets_block', 'new_design: сборные букеты'),
    ('customization_tags:render_new_design_bouquet_wish_block', 'new_design: букет по вашим желаниям'),
    ('customization_tags:render_new_design_categories_block', 'new_design: рубрики (овальные)'),
    ('customization_tags:render_new_design_collection_block', 'new_design: коллекция (карусель)'),
    ('customization_tags:render_new_design_info_block', 'new_design: гарантия качества / доставка / подарки'),
    ('customization_tags:render_new_design_social_block', 'new_design: соцсети'),
    ('customization_tags:render_new_design_reviews_block', 'new_design: отзывы'),
    ('customization_tags:render_new_design_map_block', 'new_design: карта / контакты'),
]


def get_new_design_template_tags_list():
    """
    Список тегов только для контейнеров new_design_middle и new_design_bottom.
    В админке в этих контейнерах в выпадающем списке «Шаблонный тег» показываются только они.
    """
    # Важно: первая опция пустая, чтобы в админке новый элемент не выбирал первый тег автоматически.
    return [('', '--------')] + list(NEW_DESIGN_TAG_LINES)
