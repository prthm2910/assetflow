"""apps/platform/notifications/services.py — NotificationService facade.

Uses Strategy pattern for delivery channels (in-app, email, etc.).
Add new channels by implementing NotificationChannel — no changes to service.
"""

from abc import ABC, abstractmethod
from typing import Optional

from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.platform.notifications.models import Notification


class NotificationChannel(ABC):
    """Abstract delivery channel. Implement for email, SMS, push, etc."""

    @abstractmethod
    def deliver(
        self,
        recipient,
        notification_type: str,
        title: str,
        message: str,
        related_object=None,
    ) -> bool:
        """Deliver notification. Returns True on success."""


class InAppChannel(NotificationChannel):
    """Stores notification in DB for in-app display."""

    def deliver(
        self,
        recipient,
        notification_type: str,
        title: str,
        message: str,
        related_object=None,
        organization=None,
        **kwargs,
    ) -> bool:
        content_type = None
        related_id = None
        if related_object is not None:
            content_type = ContentType.objects.get_for_model(related_object)
            related_id = related_object.pk

        Notification.objects.create(
            organization=organization or getattr(recipient, "organization", None),
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            related_content_type=content_type,
            related_object_id=related_id,
        )
        return True


class EmailChannel(NotificationChannel):
    """Sends notification via email (async via Celery)."""

    def deliver(
        self,
        recipient,
        notification_type: str,
        title: str,
        message: str,
        **kwargs,
    ) -> bool:
        try:
            from apps.platform.notifications.tasks import send_email_notification
            send_email_notification.delay(
                to=recipient.email,
                subject=title,
                body=message,
            )
            return True
        except Exception:
            # Celery not available — skip email, in-app still works
            return False


class NotificationService:
    """
    Facade: one call delivers via all configured channels.

    Usage:
        NotificationService.send(
            recipient=user,
            notification_type=NotificationType.LICENSE_EXPIRY,
            title="License expiring",
            message="JetBrains expires in 7 days",
        )
    """

    @staticmethod
    def send(
        recipient,
        notification_type: str,
        title: str,
        message: str,
        channels: Optional[list[NotificationChannel]] = None,
        related_object=None,
        organization=None,
    ) -> list:
        """
        Send notification via all channels.

        Args:
            recipient: User who receives the notification.
            notification_type: NotificationType value.
            title: Short title.
            message: Full message body.
            channels: List of channels to use. Defaults to [InAppChannel].
            related_object: Related model instance (for GFK).
            organization: Organization context.

        Returns:
            List of (channel, success) tuples.
        """
        if channels is None:
            channels = [InAppChannel()]

        results = []
        for channel in channels:
            try:
                success = channel.deliver(
                    recipient=recipient,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    related_object=related_object,
                    organization=organization,
                )
                results.append((channel.__class__.__name__, success))
            except Exception:
                results.append((channel.__class__.__name__, False))

        return results
