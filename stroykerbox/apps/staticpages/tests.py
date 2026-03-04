from django.test import TestCase
# from django.urls import reverse

from stroykerbox.apps.staticpages import models


class StaticPagesGeneric(TestCase):
    def setUp(self):
        self.staticpage_parent = models.Page.objects.create(
            title='parent title',
            key='parent_key',
            url='/parent_url/',
            text='some this page text',
            published=True
        )
        self.staticpage_child = models.Page.objects.create(
            parent=self.staticpage_parent,
            title='child title',
            key='child_key',
            url='/child_url/',
            text='some this child page text',
            published=True
        )


class StaticPagesViewsTest(StaticPagesGeneric):
    def test_parent_staticpage_detail(self):
        response = self.client.get(self.staticpage_parent.get_absolute_url())
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'staticpages/staticpage-index.html')
        self.assertTemplateUsed(response, 'staticpages/include/page.html')
        self.assertContains(response, self.staticpage_parent.title)

    def test_child_staticpage_detail(self):
        response = self.client.get(self.staticpage_child.get_absolute_url())
        self.assertEqual(200, response.status_code)
        self.assertTemplateUsed(response, 'staticpages/staticpage-index.html')
        self.assertTemplateUsed(response, 'staticpages/include/page.html')
        self.assertContains(response, self.staticpage_child.title)

    def test_parent_staticpage_as_container(self):
        response = self.client.get(self.staticpage_parent.get_absolute_url())
        self.assertNotContains(response, self.staticpage_child.title)
        self.assertTemplateNotUsed(
            response, 'staticpages/include/page-list.html')

        self.staticpage_parent.container = True
        self.staticpage_parent.save()

        response = self.client.get(self.staticpage_parent.get_absolute_url())
        self.assertContains(response, self.staticpage_child.title)
        self.assertTemplateUsed(response, 'staticpages/include/page-list.html')

    def test_staticpage_not_exists(self):
        self.staticpage_parent.published = False
        self.staticpage_parent.save()
        response = self.client.get(self.staticpage_parent.get_absolute_url())
        self.assertEqual(404, response.status_code)

    def test_staticpage_pagemanager_get_active_page(self):
        page = models.Page.objects.get_active_page(self.staticpage_parent.url)
        self.assertEqual(page, self.staticpage_parent)

        self.staticpage_parent.published = False
        self.staticpage_parent.save()
        self.assertRaises(models.Page.DoesNotExist, models.Page.objects.get_active_page, self.staticpage_parent.url)
