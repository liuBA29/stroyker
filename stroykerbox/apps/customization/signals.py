import uuid

from django.db.models import ProtectedError
from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils.translation import ugettext as _
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key

from stroykerbox.apps.customization import DEFAULT_TAG_CONTAINERS

from .models import SliderTagContainer, ColorScheme, CustomStyle, CustomScript
from .views import COLORS_CSS_CACHE_KEY
from .config import CUSTOM_STYLES_CACHE_KEY, CUSTOM_SCRIPTS_CACHE_KEY


@receiver(pre_delete, sender=SliderTagContainer, dispatch_uid='slider_tags_container_pre_delete_signal')
def protect_slider_tags_container(sender, instance, using, **kwargs):
    if instance.key in DEFAULT_TAG_CONTAINERS:
        raise ProtectedError(_('This container cannot be deleted.'), instance)


@receiver(pre_save, sender=ColorScheme)
def pre_save_colorscheme(sender, instance, **kwargs):
    qs = sender.objects.all()
    if instance.active:
        # There can be only one active scheme.
        qs.filter(active=True).update(active=False)


@receiver(post_save, sender=ColorScheme)
def clear_color_scheme_cache(sender, instance, **kwargs):
    key = make_template_fragment_key(COLORS_CSS_CACHE_KEY)
    cache.delete(key)

    # set new version value cache
    cache.set(instance.VERSION_CACHE_KEY, uuid.uuid4().hex[:8])


@receiver(post_save, sender=SliderTagContainer)
def clear_tag_container_cache(sender, instance, **kwargs):
    if instance.cache:
        cache.delete(instance.cache_key)


@receiver(post_save, sender=CustomStyle)
def clear_custom_styles_cache(sender, instance, **kwargs):
    key = make_template_fragment_key(CUSTOM_STYLES_CACHE_KEY)
    cache.delete(key)


@receiver(post_save, sender=CustomScript)
def clear_custom_scripts_cache(sender, instance, **kwargs):
    key = make_template_fragment_key(CUSTOM_SCRIPTS_CACHE_KEY)
    cache.delete(key)
