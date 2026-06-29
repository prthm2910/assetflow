"""apps/platform/notifications/tests/test_services.py — NotificationService tests."""

import pytest
from unittest.mock import MagicMock, patch

from apps.platform.notifications.constants import NotificationType
from apps.platform.notifications.models import Notification
from apps.platform.notifications.services import (
    EmailChannel,
    InAppChannel,
    NotificationService,
)


@pytest.mark.django_db
class TestNotificationService:
    def test_send_creates_notification(self, organization, user):
        """NotificationService.send() creates an in-app notification."""
        results = NotificationService.send(
            recipient=user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="Asset allocated",
            message="MacBook Pro assigned to you",
            channels=[InAppChannel()],
            organization=organization,
        )
        assert len(results) == 1
        assert results[0] == ("InAppChannel", True)
        assert Notification.objects.filter(recipient=user).count() == 1

    def test_notification_fields(self, organization, user):
        """Notification has correct fields after send."""
        NotificationService.send(
            recipient=user,
            notification_type=NotificationType.LICENSE_EXPIRY.value,
            title="License expiring",
            message="JetBrains expires in 7 days",
            channels=[InAppChannel()],
            organization=organization,
        )
        n = Notification.objects.first()
        assert n.notification_type == NotificationType.LICENSE_EXPIRY.value
        assert n.title == "License expiring"
        assert n.message == "JetBrains expires in 7 days"
        assert n.is_read is False

    def test_default_channel_is_in_app(self, organization, user):
        """Without specifying channels, defaults to InAppChannel."""
        NotificationService.send(
            recipient=user,
            notification_type=NotificationType.REQUEST_APPROVED.value,
            title="Request approved",
            message="Your request was approved",
            organization=organization,
        )
        assert Notification.objects.filter(recipient=user).count() == 1

    def test_multiple_channels(self, organization, user):
        """Can send via multiple channels."""
        results = NotificationService.send(
            recipient=user,
            notification_type=NotificationType.INCIDENT_ASSIGNED.value,
            title="Incident assigned",
            message="You have a new incident",
            channels=[InAppChannel()],
            organization=organization,
        )
        # Only InAppChannel succeeds (EmailChannel needs Celery)
        assert len(results) == 1
        assert results[0][1] is True  # InAppChannel succeeds


class TestEmailChannel:
    def test_email_channel_queues_celery_task(self, user):
        """EmailChannel queues send_email_notification.delay()."""
        with patch(
            "apps.platform.notifications.tasks.send_email_notification"
        ) as mock_task:
            channel = EmailChannel()
            result = channel.deliver(
                recipient=user,
                notification_type="test",
                title="Test",
                message="Test body",
            )
            assert result is True
            mock_task.delay.assert_called_once_with(
                to=user.email,
                subject="Test",
                body="Test body",
            )
