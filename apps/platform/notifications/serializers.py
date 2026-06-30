"""apps/platform/notifications/serializers.py — Serializers for Notification."""

from rest_framework import serializers

from apps.base.serializers import BaseSerializer
from apps.platform.notifications.models import Notification


class NotificationSerializer(BaseSerializer):
    """Full serializer for Notification."""

    recipient_email = serializers.EmailField(source="recipient.email", read_only=True)
    recipient_name = serializers.SerializerMethodField()

    class Meta(BaseSerializer.Meta):
        model = Notification
        fields = [
            "notif_id",
            "organization",
            "recipient",
            "recipient_email",
            "recipient_name",
            "notification_type",
            "title",
            "message",
            "is_read",
            "related_content_type",
            "related_object_id",
            "created_at",
            "updated_at",
        ]

    def get_recipient_name(self, obj):
        if obj.recipient:
            return obj.recipient.get_full_name() or obj.recipient.email
        return None


class NotificationListSerializer(BaseSerializer):
    """Lightweight serializer for list views."""

    class Meta(BaseSerializer.Meta):
        model = Notification
        fields = [
            "notif_id",
            "notification_type",
            "title",
            "message",
            "is_read",
            "recipient_email",
            "created_at",
        ]
