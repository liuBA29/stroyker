import os

from django.test import TestCase, RequestFactory
from django.core.exceptions import ValidationError
from django.http import QueryDict
from django.conf import settings

from .validators import validator_svg
from .templatetags import utils_tags as tags

svg_source = """<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg" width="466" height="466" viewBox="-40 -40 80 80">
        <circle r="39"/>
        <path d="M0,38a38,38 0 0 1 0,-76a19,19 0 0 1 0,38a19,19 0 0 0 0,38" fill="#fff"/>
        <circle cy="19" r="5" fill="#fff"/>
        <circle cy="-19" r="5"/>
</svg>"""


class UtilsTest(TestCase):

    def test_svg_validator(self):
        file_path = '/tmp/svg_testfile.svg'
        # wrong file
        with open(file_path, 'w') as f:
            f.write('23823792739')
        self.assertRaises(ValidationError, validator_svg, file_path)

        # true svg file
        with open(file_path, 'w') as f:
            f.write(svg_source)
        self.assertIsNone(validator_svg(file_path))

        os.remove(file_path)


class UtilsTagsTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.url = ('/')
        cls.factory = RequestFactory()

    def test_url_with_querystring_tag(self):
        kwargs = {'test_param': 'test_param_value'}
        context = {'request': self.factory.get(self.url)}
        result = tags.url_with_querystring(context, **kwargs)
        test_url_with_params = f"{self.url}?test_param={kwargs['test_param']}"
        self.assertEqual(result, test_url_with_params)

        new_request = self.factory.get(f'{test_url_with_params}')
        kwargs = {'test_param_2': 'test_param_value_2'}
        context = {'request': new_request}
        result = tags.url_with_querystring(context, **kwargs)
        self.assertEqual(
            result, f"{test_url_with_params}&test_param_2={kwargs['test_param_2']}")

    def test_url_with_querystring_tag_with_packed(self):
        dict_string = 'a=1&b=2&b=3'
        kwargs = {'_packed': QueryDict(dict_string)}
        context = {'request': self.factory.get(self.url)}
        result = tags.url_with_querystring(context, **kwargs)
        test_url_with_params = f'/?{dict_string}'
        self.assertEqual(result, test_url_with_params)

    def test_math_abs_filter(self):
        self.assertEqual(tags.math_abs(-33.555), 33.555)

    def test_sub_filter(self):
        self.assertEqual(tags.sub(4, 1), 4 - 1)

    def test_keep_tags_filter(self):
        source_string = '<h3>some h</h3><p>some text<i>some i</i></p>'
        excepted_tags = ['h3', 'i']
        # paragraph tag should be removed
        expected_string = '<h3>some h</h3>some text<i>some i</i>'
        result = tags.keep_tags(source_string, excepted_tags)
        self.assertEqual(result, expected_string)

    def test_klass_filter(self):
        """
        Get a class name of the instance as a string.
        """
        self.assertEqual(tags.klass(self), self.__class__.__name__)

    def test_settings_value_tag(self):
        result = tags.settings_value('BASE_DIR')
        self.assertEqual(result, settings.BASE_DIR)

    def test_str_to_date_filter(self):
        # date string in ISO format – yyyy-mm-dd
        date_str = '2002-02-08'
        date_format_str = '%Y.%m.%d'
        expected_string = '2002.02.08'
        self.assertEqual(tags.str_to_date(
            date_str, date_format_str), expected_string)

        # with wrong value
        wrong_date_str = '20-02-8'
        # returns the input value
        self.assertEqual(tags.str_to_date(
            wrong_date_str, date_format_str), wrong_date_str)

    def test_remove_styles_filter(self):
        source_string = '<div style="display: none;">aaa</div> bbb <b style="color:#fff">ccc</b>'
        expected_string = '<div>aaa</div> bbb <b>ccc</b>'
        self.assertEqual(tags.remove_styles(source_string), expected_string)

    def test_split_by_newline_filter(self):
        source_string = 'aaa bbb ccc'
        expected_string = 'aaa</br>bbb</br>ccc'
        self.assertEqual(tags.split_by_newline(source_string), expected_string)

    def test_multiplication_filter(self):
        self.assertEqual(tags.multiplication(3, 8), 3 * 8)

    def test_month_name_filter(self):
        from django.utils.translation import ugettext
        self.assertEqual(tags.month_name(5), ugettext('May'))
