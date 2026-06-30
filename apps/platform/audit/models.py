"""
apps/platform/audit/models.py — AuditLog model.

AuditLog entries are created automatically by Django signals in
apps/platform/audit/signals.py on every create/update/delete of
BaseModel-derived objects.

HRID: AUD-* prefix for public-facing references.
object_id: UUID of the affected object (matches all model PKs).
"""

from django.db import models

from apps.base.models import BaseModel
from apps.platform.audit.constants import AuditAction


class AuditLog(BaseModel):
    """
    Audit trail for all CRUD operations on tracked models.

    Populated by pre_save/post_save/pre_delete signals.
    """

    _display_id_prefix = "AUD"
    _display_id_field = "audit_id"

    audit_id = models.CharField(
        max_length=20, unique=True, editable=False, null=True,
        help_text="Human-readable ID (e.g. AUD7K3M9).",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="User who performed the action (from request context).",
    )
    action = models.CharField(
        max_length=20,
        choices=AuditAction.choices(),
        help_text="Type of action performed.",
    )
    model_name = models.CharField(
        max_length=100,
        help_text="Model class name (e.g. Asset, Incident).",
    )
    object_id = models.UUIDField(
        help_text="UUID primary key of the affected object.",
    )
    old_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Serialized state before the change.",
    )
    new_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Serialized state after the change.",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP address at the time of the action.",
    )
    request_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Correlation ID (X-Request-ID) for request tracing.",
    )

    class Meta:
        db_table = "audit_log"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "-created_at"],
                name="audit_org_created_idx",
            ),
            models.Index(
                fields=["model_name", "object_id"],
                name="audit_model_object_idx",
            ),
            models.Index(
                fields=["action"],
                name="audit_action_idx",
            ),
        ]

    def __str__(self):
        org_name = getattr(self.organization, "name", str(self.organization_id))
        return f"[{self.action}] {self.model_name} {self.object_id} ({org_name})"
