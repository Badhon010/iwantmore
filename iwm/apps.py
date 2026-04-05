from django.apps import AppConfig


class IwmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'iwm'

    def ready(self):
        from . import signals  # noqa: F401
