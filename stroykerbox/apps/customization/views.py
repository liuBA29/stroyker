from django.template import loader
from django.http import HttpResponse

from .models import ColorScheme

COLORS_CSS_CACHE_KEY = 'customization_colors_css'


def custom_colors_css(request):
    """
    Returns the generated css file if the site uses custom colors for the current theme.
    """
    try:
        scheme = ColorScheme.objects.get(active=True)
    except ColorScheme.DoesNotExist:
        styles = ''
    else:
        tpl = loader.get_template('customization/custom-colors-css.html')
        styles = tpl.render({
            'scheme': scheme,
        })

    response = HttpResponse(content_type='text/css')
    response['Content-Disposition'] = 'attachment; filename="custom_colors.css"'
    response.write(styles)
    return response
