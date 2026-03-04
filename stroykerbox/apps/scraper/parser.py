import re
import uuid
import json
from logging import getLogger
from urllib.parse import urlparse
from urllib.error import HTTPError
from urllib3 import PoolManager
from pyquery import PyQuery as Pq
from requests.exceptions import RequestException
from decimal import Decimal, InvalidOperation

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.utils import IntegrityError

from stroykerbox.apps.catalog import models
from stroykerbox.apps.utils.text import slugify


logger = getLogger(__name__)


class CategoryParser(object):
    """ Category parser. """
    site_address = None
    full_domain = None
    first_domain = None
    second_domain = None
    scraper = None
    _category_dom = None
    _category_parameters = None
    _parsed_products = 0

    def __init__(self, scraper):
        self.scraper = scraper
        parsed_uri = urlparse(self.scraper.category_source_url)
        self.site_address = '{uri.scheme}://{uri.netloc}'.format(uri=parsed_uri)
        self.full_domain = parsed_uri.netloc
        domain_split = self.full_domain.split('.')
        self.first_domain = domain_split[-1]
        self.second_domain = domain_split[-2]

    def parse(self):
        """ Parses category page of a target site. """
        try:
            self._category_dom = self._get_dom(self.scraper.category_source_url)
        except HTTPError as e:
            logger.exception(str(e))
            return
        if self.scraper.filter_json_attr:
            self._parse_json_parameters()
        else:
            self._parse_html_parameters()
        self._category_parameters = models.CategoryParameterMembership.objects.filter(category=self.scraper.category)
        if self.scraper.pagination_selector:
            pages = self._category_dom(self.scraper.pagination_selector)
            if len(pages) > 1:
                if self.scraper.filter_json_attr:
                    last_page = int(pages[pages.length - 1].attrib['data-page'])
                else:
                    last_page = int(pages[pages.length - 1].text)
                position = 0
                for number in range(last_page):
                    pos = position + number
                    try:
                        page_dom = self._get_dom(
                            f'{self.scraper.category_source_url}{self.scraper.page_prefix}{number + 1}')
                    except RequestException as e:
                        logger.exception(str(e))
                        continue
                    position = self._parse_product(page_dom, start_pos=pos)
            else:
                category_dom = self._get_dom(self.scraper.category_source_url)
                self._parse_product(category_dom)
        else:
            category_dom = self._get_dom(self.scraper.category_source_url)
            self._parse_product(category_dom)
        if self.scraper.filter_json_attr:
            self._walk_parameter()
        else:
            self._walk_parameter(json_source=False)
        return self._parsed_products

    def update_positions(self):
        """ Updates positions of products according a source site. """
        try:
            self._category_dom = self._get_dom(self.scraper.category_source_url)
        except HTTPError as e:
            logger.exception(str(e))
            return
        if self.scraper.pagination_selector:
            pages = self._category_dom(self.scraper.pagination_selector)
            if len(pages) > 1:
                start_pos = 0
                if self.scraper.filter_json_attr:
                    last_page = int(pages[pages.length - 1].attrib['data-page'])
                else:
                    last_page = int(pages[pages.length - 1].text)
                for number in range(last_page):
                    try:
                        page_dom = self._get_dom(
                            f'{self.scraper.category_source_url}{self.scraper.page_prefix}{number + 1}')
                    except HTTPError as e:
                        logger.exception(str(e))
                        continue
                    start_pos = self._update_products_positions(page_dom, start_pos=start_pos)
            else:
                category_dom = self._get_dom(self.scraper.category_source_url)
                self._update_products_positions(category_dom)
        else:
            category_dom = self._get_dom(self.scraper.category_source_url)
            self._update_products_positions(category_dom)

    @staticmethod
    def _get_dom(page_source, headers=None):
        """ Gets DOM object from a page source. """
        ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
        if headers is None:
            headers = {'User-Agent': ua}
        return Pq(page_source, headers=headers) if isinstance(
            page_source, str) else Pq(str(page_source), headers=headers)

    def _parse_json_parameters(self):
        """ Parses category parameters for the filter from json data. """
        filter_options = self._category_dom(self.scraper.filter_option_selector)
        json_str = filter_options.attr('json-data')
        json_obj = json.loads(json_str)
        for option in json_obj['filters']:
            if option['type'] == 'range':
                parameter, created = models.Parameter.objects.update_or_create(
                    slug=slugify(option['name'], allow_unicode=True),
                    defaults={'name': option['name'], 'data_type': 'decimal', 'widget': 'range'})
            else:
                parameter, created = models.Parameter.objects.update_or_create(
                    slug=slugify(option['name'], allow_unicode=True),
                    defaults={'name': option['name'], 'data_type': 'str', 'widget': 'checkbox'})
                for item in option['filter_items']:
                    models.ParameterValue.objects.update_or_create(
                        value_slug=slugify(item['value'], allow_unicode=True), parameter=parameter,
                        value_str=item['value'])
            models.CategoryParameterMembership.objects.update_or_create(
                category=self.scraper.category, parameter=parameter,
                defaults={'display': True, 'position': 0})

    def _parse_html_parameters(self):
        """ Parses category parameters for the filter from html data. """
        filter_options = self._category_dom(self.scraper.filter_option_selector)
        parameters_to_join = json.loads(self.scraper.product_parameters_to_join)
        for option in filter_options:
            parameter = None
            name = Pq(option)(self.scraper.filter_option_title_selector)
            name = Pq(name).text().split(',')[0]
            if name in self.scraper.parameters_to_parse.split(','):
                for n in parameters_to_join:
                    if name in parameters_to_join[n]:
                        name = n
                checkbox_values = Pq(option)(self.scraper.filter_option_checkbox_selector)
                for value in checkbox_values:
                    parameter, created = models.Parameter.objects.update_or_create(
                        slug=slugify(name, allow_unicode=True),
                        defaults={'name': name, 'data_type': 'str', 'widget': 'checkbox'})
                    param_value = Pq(value).text()
                    models.ParameterValue.objects.update_or_create(
                        value_slug=slugify(param_value, allow_unicode=True),
                        parameter=parameter, value_str=param_value)
                if parameter:
                    models.CategoryParameterMembership.objects.update_or_create(
                        category=self.scraper.category, parameter=parameter,
                        defaults={'display': True, 'position': 0})

    def _walk_parameter(self, json_source=True):
        print('walk parameters')
        parameter_names = self.scraper.filter_parameter_names_to_walk.split(';')
        if json_source:
            filter_options = self._category_dom(self.scraper.filter_option_selector)
            json_str = filter_options.attr('json-data')
            json_obj = json.loads(json_str)
            for option in json_obj['filters']:
                if option['name'] in parameter_names:
                    for item in option['filter_items']:
                        url = f'http://{self.full_domain}{item["url"]}'
                        try:
                            category_parameter_dom = self._get_dom(url)
                        except RequestException:
                            continue
                        if self.scraper.pagination_selector:
                            pages = category_parameter_dom(self.scraper.pagination_selector)
                            if len(pages) > 1:
                                last_page = int(pages[pages.length - 1].attrib['data-page'])
                                for number in range(last_page):
                                    try:
                                        page_dom = self._get_dom(f'{url}{self.scraper.page_prefix}{number + 1}')
                                    except HTTPError as e:
                                        logger.exception(str(e))
                                        continue
                                    self._walk_products(option, item, page_dom)
                            else:
                                self._walk_products(option, item, category_parameter_dom)
                        else:
                            self._walk_products(option, item, category_parameter_dom)
        else:
            filter_options = self._category_dom(self.scraper.filter_option_selector)
            for option in filter_options:
                name = Pq(option)(self.scraper.filter_option_title_selector)
                if Pq(name).text() in parameter_names:
                    checkbox_values = Pq(option)(self.scraper.filter_option_checkbox_selector)
                    for item in checkbox_values:
                        url = f'http://{self.full_domain}{Pq(item).attr("href")}'
                        try:
                            category_parameter_dom = self._get_dom(url)
                        except RequestException:
                            continue
                        if self.scraper.pagination_selector:
                            pages = category_parameter_dom(self.scraper.pagination_selector)
                            if len(pages) > 1:
                                if self.scraper.filter_json_attr:
                                    last_page = int(pages[pages.length - 1].attrib['data-page'])
                                else:
                                    last_page = int(pages[pages.length - 1].text)
                                for number in range(last_page):
                                    try:
                                        page_dom = self._get_dom(f'{url}{self.scraper.page_prefix}{number + 1}')
                                    except HTTPError as e:
                                        logger.exception(str(e))
                                        continue
                                    self._walk_products(option, item, page_dom, is_json=False)
                            else:
                                self._walk_products(option, item, category_parameter_dom, is_json=False)
                        else:
                            self._walk_products(option, item, category_parameter_dom, is_json=False)

    def _walk_products(self, option, item, dom, is_json=True):
        product_name_links = dom(self.scraper.filter_product_to_walk_selector)
        joined_params = json.loads(self.scraper.product_parameters_to_join)
        for link in product_name_links:
            product_name = Pq(link).text()
            print(product_name)
            if not is_json:
                url = f'http://{self.full_domain}{Pq(link).attr("href")}'
                try:
                    product_dom = self._get_dom(url)
                except RequestException:
                    continue
                else:
                    name = product_dom(self.scraper.product_name_selector)
                    product_name = Pq(name).text()
            product_slug = slugify(product_name, allow_unicode=True)
            try:
                product = models.Product.objects.get(slug=product_slug)
            except models.Product.DoesNotExist:
                print(f'{product_slug} does not exist')
                continue
            else:
                name = option['name'] if is_json else Pq(Pq(option)(self.scraper.filter_option_title_selector)).text()
                print(name)
                for n in joined_params:
                    if name in joined_params[n]:
                        name = n
                if name in self.scraper.parameters_to_parse.split(','):
                    print('parse', name)
                    parameter = models.Parameter.objects.get(
                        name=name)
                    pv = models.ParameterValue.objects.get(
                        parameter=parameter, value_str=item['value'] if is_json else Pq(item).text())
                    ppvm, c = models.ProductParameterValueMembership.objects.update_or_create(
                        product=product, parameter=parameter)
                    print(pv)
                    ppvm.parameter_value.add(pv)
                    print(ppvm)

    def _get_product_dom(self, path):
        if self.site_address not in path:
            path = f'{self.site_address}{path.attrib["href"]}'
        try:
            return self._get_dom(path)
        except HTTPError as e:
            logger.exception(str(e))
            return None
        except RequestException as e:
            logger.exception(str(e))
            try:
                return self._get_dom(path)
            except RequestException:
                return None

    def _parse_product(self, page_dom, start_pos=0):
        """ Parses product pages of a target site. """
        paths = page_dom(self.scraper.product_url_selector)
        position = start_pos
        for pos, path in enumerate(paths):
            position = start_pos + pos
            product_dom = self._get_product_dom(path)
            if product_dom is None:
                continue
            price_elems = product_dom(self.scraper.product_price_selector)
            price = product_dom(self.scraper.product_price_selector)[0] if len(price_elems) > 0 else None
            price_pattern = re.compile(r'\.|,|\d')
            price_decimal = Decimal(''.join(re.findall(price_pattern, Pq(price).text()))) if price is not None else None
            name = Pq(product_dom(self.scraper.product_name_selector)).text()
            description = Pq(product_dom(self.scraper.product_description_selector)).html()
            if self.scraper.product_code_selector:
                code_pattern = re.compile(r'\d')
                code_elem = product_dom(self.scraper.product_code_selector)[0]
                code = ''.join(
                    re.findall(code_pattern, Pq(code_elem).text())) if code_elem is not None else uuid.uuid4()
            else:
                if '[' in name and ']' in name:
                    code = name.split('[')[1].split(']')[0].strip()
                else:
                    code = uuid.uuid4()
            slug = slugify(name, allow_unicode=True)
            uom, uom_created = models.Uom.objects.get_or_create(name=self.scraper.product_uom_name)
            defaults = {'name': name, 'price': price_decimal,
                        'description': description, 'sku': code, 'uom': uom,
                        'published': self.scraper.product_published, 'position': position}
            try:
                product, created = models.Product.objects.update_or_create(slug=slug, defaults=defaults)
                if self.scraper.category not in product.categories.all():
                    product.categories.add(self.scraper.category)
            except IntegrityError:
                code = defaults.pop('sku')
                defaults.update({'slug': slug})
                product, created = models.Product.objects.update_or_create(sku=code, defaults=defaults)
                if self.scraper.category not in product.categories.all():
                    product.categories.add(self.scraper.category)
            if not created and self.scraper.product_params_clear:
                res = product.params.all().delete()
            self._parse_product_inline_params(product_dom, product)
            self._parse_product_images(product_dom, product)
            self._parsed_products += 1
        return position + 1

    def _update_products_positions(self, page_dom, start_pos=0):
        """ Updates product's positions according products from source site. """
        paths = page_dom(self.scraper.product_url_selector)
        position = start_pos
        for pos, path in enumerate(paths):
            position = start_pos + pos
            product_dom = self._get_product_dom(path)
            if product_dom is None:
                continue
            name = Pq(product_dom(self.scraper.product_name_selector)).text()
            slug = slugify(name)
            try:
                product = models.Product.objects.get(slug=slug)
            except models.Product.DoesNotExist:
                pass
            else:
                product.position = position
                product.save()
        return position + 1

    def _parse_product_inline_params(self, dom, product):
        """ Parses product inline params from a product page. """
        table = dom(self.scraper.product_inline_params_selector)
        trs = table('tr')
        param_units_map = json.loads(self.scraper.product_inline_params_map)
        joined_params = json.loads(self.scraper.product_parameters_to_join)
        joined_params_values = json.loads(self.scraper.product_parameter_values_to_join)
        for tr in trs:
            is_decimal = False
            tds = Pq(tr).children()
            name_td = tds[0] if len(tds) > 0 else None
            value_td = tds[1] if len(tds) > 1 else None
            if name_td is not None and value_td is not None:
                name = Pq(name_td).text()
                for n in joined_params:
                    if name in joined_params[n]:
                        name = n
                value = Pq(value_td).text()
                value_max = None
                if name in param_units_map:
                    is_decimal = True
                    units = param_units_map.get(name)
                    if 'от' in units and 'до' in units and ('от' in value or 'до' in value):
                        value_split = value.split(' ')
                        try:
                            ot_index = value_split.index('от')
                        except ValueError:
                            value = 0
                        else:
                            value = value_split[ot_index + 1].replace(',', '.').strip()
                        try:
                            do_index = value_split.index('до')
                        except ValueError:
                            value_max = None
                        else:
                            value_max = Decimal(value_split[do_index + 1].replace(',', '.').strip())
                    else:
                        for unit in param_units_map.get(name):
                            value = value.replace(unit, '').replace(',', '.').strip()
                    try:
                        value = Decimal(value)
                    except InvalidOperation as e:
                        logger.exception(str(e))
                        value = None
                else:
                    value = str(value).strip()
                    for k in joined_params_values:
                        if value in joined_params_values[k]:
                            value = k
                param_slug = slugify(name, allow_unicode=True)
                parameter = models.Parameter.objects.filter(slug=param_slug).first()
                if parameter is not None and parameter.name in self.scraper.parameters_to_parse.split(','):
                    if not is_decimal:
                        pv, pv_created = models.ParameterValue.objects.get_or_create(
                            parameter=parameter, value_str=value, value_slug=slugify(value, allow_unicode=True))
                        ppvm, ppvm_created = models.ProductParameterValueMembership.objects.update_or_create(
                            product=product, parameter=parameter)
                        ppvm.parameter_value.add(pv)
                    else:
                        models.ProductParameterValueMembership.objects.update_or_create(
                            product=product, parameter=parameter,
                            defaults={'value_decimal_low': value, 'value_decimal_high': value_max})
                else:
                    models.ProductProps.objects.update_or_create(
                        product=product, slug=slugify(name, allow_unicode=True),
                        defaults={'name': name, 'value': value})

    def _parse_product_images(self, dom, product):
        """ Parses product images. """
        images = dom(self.scraper.product_image_selector)
        image_list = []
        if self.scraper.product_old_images_delete:
            product.images.all().delete()
            for img in images:
                src = Pq(img).attr(self.scraper.product_image_src_attr)
                ext = src.split('.')[-1].lower()
                http = PoolManager()
                if self.second_domain not in src:
                    src = f'{self.second_domain}.{self.first_domain}{src}'
                if not src.startswith('https:') and not src.startswith('http:'):
                    if not src.startswith('//'):
                        src = f'http://{src}'
                    else:
                        src = f'http:{src}'
                resp = http.request('GET', src)
                if resp.status == 200:
                    ext = 'jpeg' if ext == 'jpg' or ext == 'jpeg' else 'png'
                    image_file = SimpleUploadedFile(f'image.{ext}', resp.data, content_type=f'image/{ext}')
                    image_list.append(image_file)
            if image_list:
                for image_file in image_list:
                    models.ProductImage.objects.update_or_create(product=product, image=image_file)
