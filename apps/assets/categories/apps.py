"""
apps/assets/categories/apps.py — Asset Categories app configuration.
"""

from django.apps import AppConfig


class AssetCategoriesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoAutoField"
    name = "apps.assets.categories"
    verbose_name = "Asset Categories"
