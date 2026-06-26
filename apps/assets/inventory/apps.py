"""
apps/assets/inventory/apps.py — Inventory app configuration.
"""

from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoAutoField"
    name = "apps.assets.inventory"
    verbose_name = "Asset Inventory"
