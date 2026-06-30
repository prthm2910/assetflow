"""
apps/platform/audit/apps.py — App configuration for the audit module.
"""

from django.apps import AppConfig


class AuditConfig(AppConfig):
    """Configuration for the audit log app (Module 12)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform.audit"
    label = "audit"
    verbose_name = "Audit Logs"

    def ready(self):
        """Import signals to register audit handlers when the app is ready."""
        from apps.platform.audit import signals  # noqa: F401
