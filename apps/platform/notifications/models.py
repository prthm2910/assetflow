"""apps/platform/notifications/models.py — Notification model."""

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.base.models import BaseModel
from apps.platform.notifications.constants import NotificationType


class Notification(BaseModel):
    """
    In-app notification sent to a user.

    Notifications are created by NotificationService.send() and can be
    delivered via multiple channels (in-app, email, etc.).

    Inherits from BaseModel:
    - UUID primary key, org FK, created_at / updated_at / created_by / updated_by
    - is_active, is_deleted (soft delete)
    - Auto HRID generation via _display_id_prefix / _display_id_field
    """

    _display_id_prefix = "NOT"
    _display_id_field = "notif_id"

    notif_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        help_text="Auto-generated HRID (e.g., NOT7K3M9)",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    recipient = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="User who receives this notification",
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices(),
        help_text="Type of notification",
    )

    title = models.CharField(
        max_length=255,
        help_text="Short notification title",
    )

    message = models.TextField(
        help_text="Full notification message",
    )

    is_read = models.BooleanField(
        default=False,
        help_text="Whether the recipient has read this notification",
    )

    # Related object reference — FK to model type + HRID for display
    related_content_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Type of the related object (license, request, etc.)",
    )
    related_object_id = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="HRID of the related object (e.g., LIC7K3M9, REQ9M3K1)",
    )

    class Meta:
        db_table = "notifications"
        verbose_name = "notification"
        verbose_name_plural = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        user_email = self.recipient.email if self.recipient else "Unknown"
        return f"[{self.notification_type}] {self.title} → {user_email}"


class NotificationAudit(BaseModel):
    """
    Tracks which expiry notifications have been sent.

    Prevents duplicate notifications when the daily scan runs multiple times
    or recovers from a missed run.

    Example:
        license=lic_123, threshold=30, sent_at=2026-06-01 → "already sent 30-day alert"
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="notification_audits",
    )

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        help_text="Type of the expiring object (license, asset, etc.)",
    )
    object_id = models.CharField(
        max_length=36,
        help_text="ID of the expiring object (UUID)",
    )
    content_object = GenericForeignKey("content_type", "object_id")

    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices(),
        help_text="What kind of notification was sent",
    )

    threshold_days = models.PositiveIntegerField(
        help_text="Days before expiry (30, 14, 7, 1, 0)",
    )

    sent_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this notification was sent",
    )

    class Meta:
        db_table = "notification_audits"
        verbose_name = "notification audit"
        verbose_name_plural = "notification audits"
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id", "threshold_days"]),
            models.Index(fields=["organization", "notification_type"]),
        ]
        unique_together = ["content_type", "object_id", "threshold_days", "notification_type"]

    def __str__(self):
        return f"{self.notification_type} ({self.threshold_days}d) → {self.object_id} at {self.sent_at:%Y-%m-%d}"
