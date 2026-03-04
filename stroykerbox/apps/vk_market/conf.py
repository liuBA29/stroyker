from django.utils.translation import ugettext_lazy as _

UNLOAD_VARIANT_OFF, UNLOAD_VARIANT_CHECKED, UNLOAD_VARIANT_ALL = '0', '1', '2'
UNLOAD_VARIANTS = (
    (UNLOAD_VARIANT_OFF, _('не выгружать')),
    (UNLOAD_VARIANT_CHECKED, _('выгружать отмеченные')),
    (UNLOAD_VARIANT_ALL, _('выгружать все')),
)
