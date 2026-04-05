from django.contrib.admin.apps import AdminConfig


class IwantmoreAdminConfig(AdminConfig):
    default_site = "iwm.admin.IWMAdminSite"
