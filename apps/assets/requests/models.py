"""
apps/assets/requests/models.py — AssetRequest model for employee asset requests.
"""

from django.db import models

from apps.base.models import BaseModel
from apps.assets.requests.constants import RequestPriority, RequestStatus


class AssetRequest(BaseModel):
    """
    Tracks an employee's request for a category of asset.

    An employee submits a request specifying a category (e.g. "Laptops") and
    the reason. An org admin reviews and approves or rejects it. When approved,
    the org admin proceeds to allocate a specific asset from that category.

    Status transitions:
        pending → approved | rejected
        approved → fulfilled  (when an Allocation is created externally)
        rejected → pending   (employee re-submits)

    Inherits from BaseModel:
    - UUID primary key, org FK, created_at / updated_at / created_by / updated_by
    - is_active, is_deleted, deleted_at (soft delete)
    - Auto HRID generation via _display_id_prefix / _display_id_field
    """

    # HRID config — BaseModel.save() auto-generates req_id via generate_unique_id()
    _display_id_prefix = "REQ"
    _display_id_field = "req_id"

    # Human-readable request ID (REQ + random chars, e.g. REQ7K3M9)
    # — set automatically by BaseModel.save() on first insert
    req_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        help_text="Auto-generated HRID (e.g., REQ7K3M9)",
    )

    # Organization FK — row-level isolation
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="asset_requests",
    )

    # Employee submitting the request
    requested_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.PROTECT,
        related_name="asset_requests",
    )

    # Category of asset being requested
    asset_category = models.ForeignKey(
        "categories.AssetCategory",
        on_delete=models.PROTECT,
        related_name="asset_requests",
    )

    # Justification for the request
    reason = models.TextField(
        help_text="Employee's justification for needing this asset"
    )

    # Priority level
    priority = models.CharField(
        max_length=10,
        choices=RequestPriority.choices(),
        default=RequestPriority.MEDIUM.value,
        help_text="Request priority",
    )

    # Current workflow status
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices(),
        default=RequestStatus.PENDING.value,
        help_text="Current request status",
    )

    # Who reviewed this request (null until reviewed)
    reviewed_by = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_requests",
    )

    # Admin notes from the review
    review_notes = models.TextField(
        blank=True,
        default="",
        help_text="Notes from the reviewing admin",
    )

    # When the request was reviewed
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "asset_requests"
        verbose_name = "asset request"
        verbose_name_plural = "asset requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["requested_by"]),
        ]

    def __str__(self):
        category_name = (
            self.asset_category.name if self.asset_category else "Unknown Category"
        )
        emp_name = (
            self.requested_by.user.get_full_name()
            if self.requested_by and getattr(self.requested_by, "user", None)
            else "Unknown Employee"
        )
        return f"{emp_name} requested {category_name} ({self.req_id})"
