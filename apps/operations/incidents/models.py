"""apps/operations/incidents/models.py — Incident model for asset incident tracking."""

from django.db import models

from apps.base.models import BaseModel
from apps.operations.incidents.constants import IncidentCategory, IncidentStatus


class Incident(BaseModel):
    """
    Tracks incidents reported against assets (damage, malfunction, etc.).

    Status transitions:
        reported → open → in_progress → resolved → closed

    Inherits from BaseModel:
    - UUID primary key, org FK, created_at / updated_at / created_by / updated_by
    - is_active, is_deleted (soft delete)
    - Auto HRID generation via _display_id_prefix / _display_id_field
    """

    # HRID config — BaseModel.save() auto-generates inc_id
    _display_id_prefix = "INC"
    _display_id_field = "inc_id"

    # Human-readable incident ID (INC + random chars, e.g. INC7K3M9)
    inc_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        help_text="Auto-generated HRID (e.g., INC7K3M9)",
    )

    # Organization FK — row-level isolation
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="incidents",
    )

    # Asset the incident is about
    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="incidents",
    )

    # Employee who reported the incident
    reported_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="reported_incidents",
    )

    # Short summary of the incident
    title = models.CharField(
        max_length=300,
        help_text="Brief title for the incident",
    )

    # Detailed description
    description = models.TextField(
        help_text="Detailed description of the incident",
    )

    # Incident category — required, set by human (or accepted from AI suggestion endpoint)
    category = models.CharField(
        max_length=50,
        choices=IncidentCategory.choices(),
        help_text="Incident category",
    )

    # Current workflow status
    status = models.CharField(
        max_length=20,
        choices=IncidentStatus.choices(),
        default=IncidentStatus.REPORTED.value,
        help_text="Current incident status",
    )

    # Employee assigned to handle the incident
    assigned_to = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_incidents",
        help_text="Employee assigned to handle this incident",
    )

    # Notes from the resolution
    resolution_notes = models.TextField(
        blank=True,
        default="",
        help_text="Notes on how the incident was resolved",
    )

    # List of attachment file URLs
    attachments = models.JSONField(
        default=list,
        blank=True,
        help_text="List of attachment file URLs",
    )

    # When the incident was resolved
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the incident was marked resolved",
    )

    # When the incident was closed
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the incident was closed",
    )

    class Meta:
        db_table = "incidents"
        verbose_name = "incident"
        verbose_name_plural = "incidents"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["asset"]),
            models.Index(fields=["reported_by"]),
        ]

    def __str__(self):
        asset_name = self.asset.name if self.asset else "Unknown Asset"
        reporter_name = (
            self.reported_by.user.get_full_name()
            if self.reported_by and getattr(self.reported_by, "user", None)
            else "Unknown Employee"
        )
        return f"{reporter_name} reported {asset_name}: {self.title} ({self.inc_id})"
