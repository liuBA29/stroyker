from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomFormResult
from .tasks import process_new_results_from_custom_form


@receiver(post_save, sender=CustomFormResult)
def new_custom_form_request(sender, instance, created, **kwargs):
    if not created:
        return

    process_new_results_from_custom_form.delay(instance.pk)
