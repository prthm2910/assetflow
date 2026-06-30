"""
apps/platform/audit/views.py — AuditLog ViewSet.

Read-only, org-scoped, filterable by model_name, action, user, and date range.
- Super admin: sees all audit logs across all organizations
- Org admin: sees only their organization's audit logs
- Employee: no access (scope_for_employee returns empty queryset)
"""

from rest_framework.permissions import IsAuthenticated

from apps.base.response import success_response
from apps.base.viewsets import BaseViewSet
from apps.platform.audit.models import AuditLog
from apps.platform.audit.serializers import (
    AuditLogListSerializer,
    AuditLogSerializer,
)


class AuditLogViewSet(BaseViewSet):
    """Read-only audit log viewer. Super admin + org admin only."""

    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "audit_id"
    lookup_value_regex = "[\\w]+"
    ordering_fields = ["created_at", "model_name", "action"]
    ordering = ["-created_at"]
    search_fields = ["model_name", "action", "ip_address"]
    filterset_fields = ["model_name", "action", "user"]

    def get_serializer_class(self):
        if self.action == "list":
            return AuditLogListSerializer
        return AuditLogSerializer

    def get_queryset(self):
        return AuditLog.objects.select_related("user", "organization")

    def scope_for_employee(self, queryset):
        """Employees cannot view audit logs."""
        return queryset.none()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return success_response(
                data=self.get_paginated_response(serializer.data).data,
                message="Audit logs retrieved successfully",
            )
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            data=serializer.data, message="Audit logs retrieved successfully"
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            data=serializer.data, message="Audit log retrieved successfully"
        )
