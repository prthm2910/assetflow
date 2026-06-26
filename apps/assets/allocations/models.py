"""
apps/assets/allocations/models.py — Allocation model for asset assignment.
"""

from django.db import models

from apps.base.models import BaseModel


class Allocation(BaseModel):
    """
    Tracks the assignment of an asset to an employee within an organization.

    One active allocation per asset at a time. When an asset is transferred or
    returned, the existing record's `returned_at` is set (not deleted or replaced
    by a new record). A full history of all allocations (active and past) is always
    queryable via the list endpoint.

    Inherits from BaseModel:
    - UUID primary key, org FK, created_at / updated_at / created_by / updated_by
    - is_active, is_deleted, deleted_at (soft delete)
    - Auto HRID generation via _display_id_prefix / _display_id_field
    """

    # HRID config — BaseModel.save() auto-generates alloc_id via generate_unique_id()
    _display_id_prefix = "ALC"
    _display_id_field = "alloc_id"

    # Human-readable allocation ID (ALC + random chars, e.g. ALC7K3M9)
    # — set automatically by BaseModel.save() on first insert
    alloc_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        help_text="Auto-generated HRID (e.g., ALC7K3M9)",
    )

    # Organization FK — row-level isolation
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="allocations",
    )

    # Asset being allocated
    asset = models.ForeignKey(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="allocations",
    )

    # Employee receiving the asset
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="asset_allocations",
    )

    # Who performed the allocation
    allocated_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="allocations_made",
    )

    # When the asset was allocated
    allocated_at = models.DateTimeField(auto_now_add=True)

    # When the asset was returned — null means the allocation is still active
    returned_at = models.DateTimeField(null=True, blank=True)

    # Optional notes about this allocation
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "allocations"
        verbose_name = "allocation"
        verbose_name_plural = "allocations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["asset", "returned_at"]),
            models.Index(fields=["employee"]),
        ]
        constraints = [
            # Prevent double-allocation at DB level
            models.UniqueConstraint(
                fields=["asset"],
                condition=models.Q(returned_at__isnull=True),
                name="unique_active_allocation",
            )
        ]

    def __str__(self):
        asset_name = self.asset.name if self.asset else "Unknown Asset"
        emp_name = (
            self.employee.user.get_full_name()
            if self.employee and getattr(self.employee, "user", None)
            else "Unknown Employee"
        )
        return f"{asset_name} -> {emp_name} ({self.alloc_id})"

    @property
    def is_current(self):
        """True when the asset is still allocated (not returned)."""
        return self.returned_at is None
