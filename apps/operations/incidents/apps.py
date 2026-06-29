"""apps/operations/incidents/apps.py — AppConfig for the incidents app."""

from django.apps import AppConfig


class IncidentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.operations.incidents"
    verbose_name = "Incidents"
