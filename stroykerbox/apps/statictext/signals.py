from django.db.models.signals import post_save, post_delete
from django.core.cache import cache
from django.dispatch import receiver
from django.core.cache.utils import make_template_fragment_key

from stroykerbox.apps.custom_forms.models import CustomForm, CustomFormField

from .models import Statictext


def delete_cache(st_key):
    key = make_template_fragment_key('statictext', [st_key])
    cache.delete(key)


@receiver(post_save, sender=Statictext)
def on_save_statictext(sender, instance, *args, **kwargs):
    delete_cache(instance.key)


@receiver(post_delete, sender=Statictext)
def on_delete_statictext(sender, instance, *args, **kwargs):
    delete_cache(instance.key)


@receiver(post_save, sender=CustomFormField)
@receiver(post_save, sender=CustomForm)
def on_save_custom_form(sender, instance, *args, **kwargs):
    for key in Statictext.objects.filter(use_custom_form=True).values_list('key', flat=True):
        delete_cache(key)


@receiver(post_delete, sender=CustomFormField)
@receiver(post_delete, sender=CustomForm)
def on_delete_custom_form(sender, instance, **kwargs):
    for key in Statictext.objects.filter(use_custom_form=True).values_list('key', flat=True):
        delete_cache(key)
