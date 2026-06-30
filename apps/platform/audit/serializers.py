"""
apps/platform/audit/serializers.py — Serializers for AuditLog.

AuditLogSerializer: full detail with changes snapshot (old/new).
AuditLogListSerializer: lightweight for list views (excludes data blobs).
"""

from rest_framework import serializers

from apps.base.serializers import BaseSerializer
from apps.platform.audit.models import AuditLog


class AuditLogListSerializer(BaseSerializer):
    """Lightweight serializer for list views — excludes full data blobs."""

    user_email = serializers.CharField(
        source="user.email", read_only=True, default=None
    )
    user_name = serializers.SerializerMethodField()

    class Meta(BaseSerializer.Meta):
        model = AuditLog
        fields = [
            "audit_id",
            "organization",
            "user",
            "user_email",
            "user_name",
            "action",
            "model_name",
            "object_id",
            "ip_address",
            "request_id",
            "path",
            "created_at",
            "updated_at",
        ]

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return None


class AuditLogSerializer(BaseSerializer):
    """Full detail serializer — includes changes snapshot."""

    user_email = serializers.CharField(
        source="user.email", read_only=True, default=None
    )
    user_name = serializers.SerializerMethodField()

    class Meta(BaseSerializer.Meta):
        model = AuditLog
        fields = [
            "audit_id",
            "organization",
            "user",
            "user_email",
            "user_name",
            "action",
            "model_name",
            "object_id",
            "changes",
            "ip_address",
            "request_id",
            "path",
            "created_at",
            "updated_at",
        ]

    def get_user_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.email
        return None
