from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'

    def ready(self):
        from . import signals  # noqa: F401
        from .bootstrap import schedule_default_superuser_creation

        schedule_default_superuser_creation()
