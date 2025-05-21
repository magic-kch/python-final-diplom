from jet.dashboard.dashboard import AppIndexDashboard
from jet.dashboard.dashboard_modules import google_analytics
from jet.dashboard import modules
from jet.dashboard.dashboard import Dashboard


class CustomIndexDashboard(Dashboard):
    columns = 3

    def init_with_context(self, context):
        self.available_children.append(modules.LinkList)
        self.add_module(modules.LinkList(
            'Quick links',
            layout='inline',
            children=[
                ['Users', '/admin/auth/user/'],
                ['Products', '/admin/backend/product/'],
                ['Orders', '/admin/backend/order/'],
                ['Shops', '/admin/backend/shop/'],
            ]
        ))

        self.available_children.append(modules.AppList)
        self.add_module(modules.AppList(
            'Applications',
            exclude=('auth.*',)
        ))

        self.available_children.append(modules.ModelList)
        self.add_module(modules.ModelList(
            'Authentication',
            models=('auth.*',)
        ))

        self.available_children.append(modules.RecentActions)
        self.add_module(modules.RecentActions(
            'Recent Actions',
            15,
        ))


class CustomAppIndexDashboard(AppIndexDashboard):
    def init_with_context(self, context):
        self.available_children.append(modules.ModelList)
        self.add_module(modules.ModelList(
            title='Models',
            models=self.models
        ))

        self.available_children.append(modules.RecentActions)
        self.add_module(modules.RecentActions(
            'Recent Actions',
            include_list=self.models,
            limit=5
        ))
