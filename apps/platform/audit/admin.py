"""
apps/platform/audit/admin.py — Django admin registration for AuditLog.
"""

from django.contrib import admin

from apps.platform.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "action",
        "model_name",
        "object_id",
        "user_email",
        "organization_name",
        "ip_address",
        "created_at",
    ]
    list_filter = ["action", "model_name", "organization", "created_at"]
    search_fields = ["model_name", "user__email", "ip_address", "request_id"]
    readonly_fields = [
        "action",
        "model_name",
        "object_id",
        "organization",
        "user",
        "old_data",
        "new_data",
        "ip_address",
        "request_id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    def user_email(self, obj):
        return obj.user.email if obj.user else "—"

    user_email.short_description = "User"

    def organization_name(self, obj):
        return obj.organization.name if obj.organization else "—"

    organization_name.short_description = "Organization"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
