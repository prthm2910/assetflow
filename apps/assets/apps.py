"""
apps/assets/apps.py — Assets app configuration.
"""

from django.apps import AppConfig


class AssetsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoAutoField"
    name = "apps.assets"
    verbose_name = "Assets"
