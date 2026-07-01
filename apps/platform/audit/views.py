"""
apps/platform/audit/views.py — AuditLog ViewSet.

Read-only audit log viewer. Super admin + org admin only.
- Super admin: sees all audit logs across all organizations
- Org admin: sees only their organization's audit logs
- Employee: no access (read_roles restricts + scope_for_employee returns empty)
"""

from apps.base.constants import UserRole
from apps.base.viewsets import BaseViewSet
from apps.platform.audit.models import AuditLog
from apps.platform.audit.serializers import (
    AuditLogListSerializer,
    AuditLogSerializer,
)


class AuditLogViewSet(BaseViewSet):
    """Read-only audit log viewer. Super admin + org admin only."""

    serializer_class = AuditLogSerializer
    lookup_field = "audit_id"
    lookup_value_regex = "[\\w]+"
    ordering_fields = ["created_at", "model_name", "action"]
    ordering = ["-created_at"]
    search_fields = ["model_name", "action", "ip_address"]
    filterset_fields = ["model_name", "action", "user"]

    read_roles = [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]

    def get_serializer_class(self):
        if self.action == "list":
            return AuditLogListSerializer
        return AuditLogSerializer

    def get_queryset(self):
        return AuditLog.objects.select_related("user", "organization")

    def scope_for_employee(self, queryset):
        """Employees cannot view audit logs."""
        return queryset.none()
