"""apps/operations/licenses/apps.py — AppConfig for the licenses app."""

from django.apps import AppConfig


class LicensesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.operations.licenses"
    verbose_name = "Licenses"
