"""apps/platform/notifications/views.py — ViewSets for Notification."""

from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from apps.base.response import success_response
from apps.base.viewsets import BaseViewSet
from apps.platform.notifications.models import Notification
from apps.platform.notifications.serializers import (
    NotificationSerializer,
    NotificationListSerializer,
)


class NotificationViewSet(BaseViewSet):
    """
    Notification management for the current user.

    - All authenticated users: see their own notifications
    - Custom actions: mark_read, mark_all_read, unread_count
    """

    lookup_field = "notif_id"
    lookup_value_regex = r"[\w-]+"
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    search_fields = ["title", "message"]
    filterset_fields = ["notification_type", "is_read"]

    def get_permissions(self):
        return [IsAuthenticated()]

    def get_queryset(self):
        """Users see only their own notifications."""
        queryset = Notification.objects.filter(
            recipient=self.request.user,
            is_deleted=False,
        ).select_related("recipient", "organization")
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return NotificationListSerializer
        return NotificationSerializer

    @action(detail=True, methods=["patch"], url_path="read")
    def mark_read(self, request, notif_id=None):
        """Mark a single notification as read."""
        instance = self.get_object()
        instance.is_read = True
        instance.save(update_fields=["is_read", "updated_at"])
        return success_response(
            data=NotificationSerializer(instance).data,
            message="Notification marked as read.",
        )

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        """Mark all notifications as read for the current user."""
        count = self.get_queryset().filter(is_read=False).update(
            is_read=True,
            updated_at=timezone.now(),
        )
        return success_response(
            data={"count": count},
            message=f"{count} notification(s) marked as read.",
        )

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        """Get unread notification count for the current user."""
        count = self.get_queryset().filter(is_read=False).count()
        return success_response(data={"count": count})
