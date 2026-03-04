from django.utils.translation import ugettext_lazy as _
from grappelli.dashboard import Dashboard, modules


class CustomIndexDashboard(Dashboard):
    """
    Custom index dashboard for www.
    """

    def init_with_context(self, context):
        # append a group for "Administration" & "Applications"
        self.children.append(modules.AppList(
            _('Applications'),
            column=1,
            collapsible=True,
            css_classes=('collapse closed',),
            exclude=('django.contrib.*', 'constance.*'),
        ))

        self.children.append(modules.AppList(
            _('Administration'),
            column=2,
            collapsible=True,
            models=('django.contrib.*', 'constance.*', 'django_rq.*'),
        ))

        # append a recent actions module
        self.children.append(modules.RecentActions(
            _('Recent Actions'),
            limit=20,
            collapsible=True,
            column=3,
        ))
        self.children.append(modules.LinkList(
            _('Media Management'),
            column=2,
            children=[
                {
                    'title': _('FileBrowser'),
                    'url': '/admin/filebrowser/browse/',
                    'external': False,
                },
            ]
        ))
