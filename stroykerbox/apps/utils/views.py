from django.utils.translation import ugettext as _

from django.core.management import call_command
from django.http import HttpResponseRedirect
from django.contrib import messages


def clear_cache(request):
    call_command('mptt_category_rebuild', verbosity=0)
    redirect_url = request.GET.get('next', '/admin/')
    messages.success(request, _('Кэш данных проекта очищен.'))
    return HttpResponseRedirect(redirect_url)


def clear_thumbnail_cache(request):
    call_command('thumbnail', 'clear_delete_referenced', verbosity=0)
    redirect_url = request.GET.get('next', '/admin/')
    messages.success(request, _('Кэш изображений очищен.'))
    return HttpResponseRedirect(redirect_url)
