from django.test import TestCase
from django.template import Context, Template

from stroykerbox.apps.statictext.models import Statictext


class StatictextTagsTest(TestCase):
    def setUp(self):
        self.statictext = Statictext.objects.create(
            key='some_key', text='some text')

    def test_render_statictext_tag(self):
        out = Template(
            "{% load statictext_tags %}"
            "{% render_statictext 'some_key' %}"
        ).render(Context())
        self.assertEqual(self.statictext.text, out)

    def test_render_statictext_tag_with_remove_paragraph(self):
        old_text = self.statictext.text
        new_text = f'<p>{old_text}</p>'
        self.statictext.text = new_text
        self.statictext.save()
        out = Template(
            "{% load statictext_tags %}"
            "{% render_statictext 'some_key' %}"
        ).render(Context({}))
        self.assertEqual(new_text, out)

        # with paragraph deletion
        out = Template(
            "{% load statictext_tags %}"
            "{% render_statictext 'some_key' 'True' %}"
        ).render(Context({}))
        self.assertNotEqual(new_text, out)
        self.assertEqual(old_text, out)

    def test_render_statictext_tag_with_wrong_key(self):
        out = Template(
            "{% load statictext_tags %}"
            "{% render_statictext 'wrong key' %}"
        ).render(Context({}))
        self.assertEqual('', out)

    def test_render_statictext_tag_with_as(self):
        out = Template(
            "{% load statictext_tags %}"
            "{% render_statictext 'some_key' as statictext %}"
            "{{ statictext }}"
        ).render(Context())
        self.assertEqual(self.statictext.text, out)
