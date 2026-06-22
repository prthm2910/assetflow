"""
apps/apps.py — Apps package configuration.
"""
from django.apps import AppConfig


class AppsConfig(AppConfig):
    """Configuration for the AssetFlow apps package."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps'
    label = 'apps'
