"""apps/platform/notifications/apps.py — AppConfig for the notifications app."""

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform.notifications"
    verbose_name = "Notifications"
