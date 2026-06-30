"""apps/platform/notifications/tests/test_models.py — Notification model tests."""

import pytest

from apps.platform.notifications.constants import NotificationType
from apps.platform.notifications.models import Notification


@pytest.mark.django_db
class TestNotificationModel:
    def test_notification_created(self, organization, user):
        """Basic notification creation."""
        n = Notification.objects.create(
            organization=organization,
            recipient=user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="Asset allocated",
            message="MacBook Pro assigned to you",
        )
        assert n.id is not None
        assert n.is_read is False

    def test_default_is_read_false(self, organization, user):
        """New notifications default to unread."""
        n = Notification.objects.create(
            organization=organization,
            recipient=user,
            notification_type=NotificationType.REQUEST_APPROVED.value,
            title="Request approved",
            message="Your laptop request was approved",
        )
        assert n.is_read is False

    def test_mark_as_read(self, organization, user):
        """Mark notification as read."""
        n = Notification.objects.create(
            organization=organization,
            recipient=user,
            notification_type=NotificationType.REQUEST_APPROVED.value,
            title="Request approved",
            message="Your laptop request was approved",
        )
        n.is_read = True
        n.save(update_fields=["is_read"])
        n.refresh_from_db()
        assert n.is_read is True

    def test_str_with_recipient(self, organization, user):
        """__str__ shows type, title, and recipient email."""
        n = Notification.objects.create(
            organization=organization,
            recipient=user,
            notification_type=NotificationType.LICENSE_EXPIRY.value,
            title="License expiring",
            message="JetBrains expires in 7 days",
        )
        s = str(n)
        assert "license_expiry" in s
        assert "License expiring" in s
        assert user.email in s

    def test_soft_delete(self, organization, user):
        """delete() performs soft-delete."""
        n = Notification.objects.create(
            organization=organization,
            recipient=user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="Test",
            message="Test",
        )
        n_id = n.id
        n.delete()
        assert not Notification.objects.filter(id=n_id).exists()
        assert Notification.objects.all_with_deleted().filter(id=n_id).exists()

    def test_notification_type_choices(self):
        """NotificationType enum provides valid choices."""
        choices = NotificationType.choices()
        assert len(choices) >= 6
        choice_values = [c[0] for c in choices]
        assert NotificationType.ASSET_ALLOCATED.value in choice_values
        assert NotificationType.LICENSE_EXPIRY.value in choice_values
