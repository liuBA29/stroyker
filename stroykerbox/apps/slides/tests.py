from io import BytesIO

from PIL import Image

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.template import Context, Template

from model_bakery import baker
from stroykerbox.apps.slides.templatetags import slide_tags


class SlidesTagsTest(TestCase):

    def setUp(self):
        data = BytesIO()
        Image.new('RGB', (100, 100)).save(data, 'JPEG')
        data.seek(0)
        uploaded_file = SimpleUploadedFile('image.jpeg', data.getvalue())
        self.big_slides = baker.make('BigSlide', _create_files=True, _quantity=3, image=uploaded_file)

    def test_render_big_slides_tag(self):
        out = Template(
            "{% load slide_tags %}"
            "{% render_big_slides %}"
        ).render(Context())
        self.assertIn(f'<img src="{self.big_slides[0].image.url}"',
                      out)

    def test_render_big_slides_tag_as_result(self):
        result = slide_tags.render_big_slides(Context())
        self.assertEqual(result['slides'].count(), len(self.big_slides))

    def test_render_big_slides_tag_as_result_with_nopublished(self):
        self.big_slides[0].published = False
        self.big_slides[0].save()
        result = slide_tags.render_big_slides(Context())
        self.assertEqual(result['slides'].count(), len(self.big_slides) - 1)
