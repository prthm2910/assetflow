"""
apps/base/apps.py — App configuration for the base utilities module.
"""
from django.apps import AppConfig


class BaseConfig(AppConfig):
    """Configuration for the base utilities app (Module 1)."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.base'
    label = 'base'
    verbose_name = 'Base Utilities'

    def ready(self):
        """Import signals to register them when the app is ready."""
        from apps.base import signals  # noqa: F401
