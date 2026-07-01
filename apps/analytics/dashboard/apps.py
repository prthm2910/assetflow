from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """Configuration for the analytics dashboard app (Module 14)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics.dashboard"
    label = "analytics_dashboard"
