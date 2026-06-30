"""apps/platform/notifications/tests/test_views.py — Notification API tests."""

import pytest

from apps.platform.notifications.constants import NotificationType
from apps.platform.notifications.models import Notification


@pytest.mark.django_db
class TestNotificationViews:
    def test_list_notifications(self, employee_client, organization, user):
        """Users see their own notifications."""
        Notification.objects.create(
            organization=organization,
            recipient=user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="Asset allocated",
            message="MacBook Pro assigned",
        )
        response = employee_client.get("/api/v1/notifications/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_unauthenticated_denied(self, api_client):
        response = api_client.get("/api/v1/notifications/")
        assert response.status_code == 401

    def test_user_sees_only_own_notifications(
        self, employee_client, organization, user, second_employee
    ):
        """Users don't see other users' notifications."""
        Notification.objects.create(
            organization=organization,
            recipient=user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="For user",
            message="Message",
        )
        Notification.objects.create(
            organization=organization,
            recipient=second_employee.user,
            notification_type=NotificationType.REQUEST_APPROVED.value,
            title="For second",
            message="Message",
        )
        response = employee_client.get("/api/v1/notifications/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_retrieve_notification(self, employee_client, organization, user):
        n = Notification.objects.create(
            organization=organization,
            recipient=user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="Asset allocated",
            message="MacBook Pro assigned",
        )
        response = employee_client.get(f"/api/v1/notifications/{n.notif_id}/")
        assert response.status_code == 200
        assert response.json()["data"]["title"] == "Asset allocated"

    def test_mark_read(self, employee_client, organization, user):
        n = Notification.objects.create(
            organization=organization,
            recipient=user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="Test",
            message="Test",
        )
        assert n.is_read is False
        response = employee_client.patch(f"/api/v1/notifications/{n.notif_id}/read/")
        assert response.status_code == 200
        n.refresh_from_db()
        assert n.is_read is True

    def test_mark_all_read(self, employee_client, organization, user):
        Notification.objects.create(
            organization=organization, recipient=user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="Test 1", message="Test",
        )
        Notification.objects.create(
            organization=organization, recipient=user,
            notification_type=NotificationType.REQUEST_APPROVED.value,
            title="Test 2", message="Test",
        )
        response = employee_client.post("/api/v1/notifications/mark-all-read/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 2
        assert Notification.objects.filter(recipient=user, is_read=False).count() == 0

    def test_unread_count(self, employee_client, organization, user):
        Notification.objects.create(
            organization=organization, recipient=user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="Unread", message="Test",
        )
        Notification.objects.create(
            organization=organization, recipient=user,
            notification_type=NotificationType.REQUEST_APPROVED.value,
            title="Also unread", message="Test",
        )
        # Mark one as read
        n = Notification.objects.filter(recipient=user).first()
        n.is_read = True
        n.save()

        response = employee_client.get("/api/v1/notifications/unread-count/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_filter_by_is_read(self, employee_client, organization, user):
        Notification.objects.create(
            organization=organization, recipient=user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="Unread", message="Test", is_read=False,
        )
        n = Notification.objects.create(
            organization=organization, recipient=user,
            notification_type=NotificationType.REQUEST_APPROVED.value,
            title="Read", message="Test", is_read=True,
        )
        response = employee_client.get("/api/v1/notifications/?is_read=true")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_cannot_mark_others_notification(self, employee_client, user, second_employee):
        """User can't mark another user's notification as read."""
        n = Notification.objects.create(
            organization=user.organization,
            recipient=second_employee.user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="Not yours",
            message="Message",
        )
        response = employee_client.patch(f"/api/v1/notifications/{n.notif_id}/read/")
        assert response.status_code == 404

    def test_empty_list_returns_zero(self, employee_client):
        """Empty notification list returns count=0."""
        response = employee_client.get("/api/v1/notifications/")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 0

    def test_filter_by_notification_type(self, employee_client, organization, user):
        """Filter notifications by type."""
        Notification.objects.create(
            organization=organization, recipient=user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="Allocated", message="Test",
        )
        Notification.objects.create(
            organization=organization, recipient=user,
            notification_type=NotificationType.REQUEST_APPROVED.value,
            title="Approved", message="Test",
        )
        response = employee_client.get(
            f"/api/v1/notifications/?notification_type={NotificationType.ASSET_ALLOCATED.value}"
        )
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_search_notifications(self, employee_client, organization, user):
        """Search notifications by title/message."""
        Notification.objects.create(
            organization=organization, recipient=user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="MacBook Pro assigned", message="Your new laptop",
        )
        Notification.objects.create(
            organization=organization, recipient=user,
            notification_type=NotificationType.REQUEST_APPROVED.value,
            title="Request approved", message="Laptop request approved",
        )
        response = employee_client.get("/api/v1/notifications/?search=MacBook")
        assert response.status_code == 200
        assert response.json()["data"]["count"] == 1

    def test_notification_with_related_object(self, employee_client, organization, user, asset):
        """Notification stores related object type + HRID."""
        from django.contrib.contenttypes.models import ContentType
        from apps.assets.inventory.models import Asset

        ct = ContentType.objects.get_for_model(Asset)
        n = Notification.objects.create(
            organization=organization,
            recipient=user,
            notification_type=NotificationType.ASSET_ALLOCATED.value,
            title="Asset allocated",
            message="MacBook Pro assigned",
            related_content_type=ct,
            related_object_id=asset.asset_id,  # HRID, not UUID
        )

        response = employee_client.get(f"/api/v1/notifications/{n.notif_id}/")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["related_object_id"] == asset.asset_id
