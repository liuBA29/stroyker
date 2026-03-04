import re
import base64
from urllib.parse import urlparse, parse_qs

from django.core.cache import cache
from django.http.response import FileResponse
from django.urls import Resolver404, resolve
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import ugettext as _
from django.shortcuts import redirect

from stroykerbox.apps.seo.models import MetaTag
try:
    from stroykerbox.apps.seo.templatetags.cache import tags_cache_key
except ImportError:
    tags_cache_key = None

H1_RE = re.compile(r'<h1(.*?)>.*?</h1>', re.U | re.I | re.S)

IGNORED_MATCHING_URL_PARAMS_RE = re.compile(r'utm')


class SeoMiddleware(MiddlewareMixin):
    """
    Middleware for SEO: breadcrumbs, title, meta tags
    """

    EXCLUDE_PATHS = ['/admin/', '/media/']

    def process_request(self, request):

        # add seo object to request if this page exists
        parsed = urlparse(request.path_info)

        # https://redmine.fancymedia.ru/issues/12723
        if parsed.path.endswith('//'):
            redirect_path = parsed.path.rsplit('//')[0]
            if not redirect_path.endswith('/'):
                redirect_path += '/'
            return redirect(redirect_path)

        if not request.is_ajax() and not any(parsed.path.startswith(p) for p in self.EXCLUDE_PATHS):
            try:
                resolve(parsed.path)
            except Resolver404:
                pass
            else:
                request.seo = Seo(request)
        return None

    def process_response(self, request, response):
        if isinstance(response, FileResponse) or (response.get('Content-Type') and 'image' in response['Content-Type']):
            pass
        else:
            if hasattr(request, 'seo') and request.seo.overwrite is not None:
                if request.seo.overwrite.h1:
                    response.content = H1_RE.sub(r'<h1\1>{}</h1>'.format(request.seo.overwrite.h1),
                                                 response.content.decode('utf-8'), 1)
            if tags_cache_key:
                try:
                    cache_key = str(base64.b64decode(
                        tags_cache_key), 'utf-8').split(':')
                except:  # noqa
                    cache_key = []
                if len(cache_key) == 2:
                    response[cache_key[0]] = cache_key[1]
        return response


class Seo(MiddlewareMixin):
    """
    This class is appended to the current request and stores
    information about breadcrumbs, title, meta tags
    """

    CACHE_KEY = 'seo_all_meta_tags'

    def __init__(self, request):
        self.request = request
        self.meta_keywords = getattr(self, 'meta_keywords', '')
        self.ai_keywords = getattr(self, 'ai_keywords', '')
        self.meta_description = getattr(self, 'meta_description', '')

        self.h1 = None
        # title separator
        self.title_glue = ' — '
        self.title = []
        self.breadcrumbs = [('/', _('Homepage'))]
        self.seo_text = self.overwrite = None
        self.all_meta_tags = cache.get_or_set(self.CACHE_KEY,
                                              MetaTag.objects.all(), 60 * 60 * 60)

        url = request.get_full_path()
        url_path = request.path
        url_params = parse_qs(urlparse(url).query, keep_blank_values=True)
        # Remove unneeded params from the requested query string
        url_params = {k: v for k, v in url_params.items(
        ) if not IGNORED_MATCHING_URL_PARAMS_RE.match(k)}

        for meta_tag in self.all_meta_tags:
            meta_tag_parsed_url = urlparse(meta_tag.url)
            if url_path == meta_tag_parsed_url.path and url_params == parse_qs(meta_tag_parsed_url.query, True):
                self.overwrite = meta_tag
                self.seo_text = meta_tag.seo_text
                break

    def _make_parameters_list(self, form):
        """
        Returns list of parameters names and checked values pairs.
        :param form: filter form object
        :return: list of parameters names and checked values pairs
        """
        param_dict = dict(self.request.GET)
        params = []
        for param_slug in self.request.GET:
            if param_slug in form.param_names_by_slug:
                param_value = ' '.join([' '.join(form.choice_names_by_slug[choice_slug].split()[:-1])
                                        for choice_slug in param_dict[param_slug]
                                        if choice_slug in form.choice_names_by_slug])
                params.append('{param_name} {param_value}'
                              .format(param_name=form.param_names_by_slug[param_slug], param_value=param_value))
        return params

    def override_seo_tags_with_catalog_filters(self, category, form):
        """
        Overrides seo tags on the catalog category page with filters.
        :param category: category object
        :param form: filter form object
        """
        params = self._make_parameters_list(form)

        # TITLE
        self.request.seo.title.clear()
        self.title = [category.name]
        if params:
            self.title = [', '.join(params)] + self.title
        self.title_glue = ', '

        # H1 META KEYWORDS
        self.h1 = self.meta_keywords = ', '.join([category.name] + params)

        # https://redmine.fancymedia.ru/issues/12714
        self.category_filter_params = params
