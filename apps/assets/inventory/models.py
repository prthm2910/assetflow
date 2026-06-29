"""
apps/assets/inventory/models.py — Asset model for inventory management.
"""

from django.db import models

from apps.assets.inventory.constants import AssetStatus
from apps.base.models import BaseModel


class Asset(BaseModel):
    """
    Asset tracked in the inventory system.

    Each asset has a unique HRID (AST + random chars), belongs to one
    organization, optionally belongs to a category (via AssetCategory), and can
    be assigned to one employee.

    Inherits from BaseModel:
    - UUID primary key, org FK, created_at / updated_at / created_by / updated_by
    - is_active, is_deleted, deleted_at (soft delete)
    - Auto HRID generation via _display_id_prefix / _display_id_field
    """

    # HRID config — BaseModel.save() auto-generates asset_id via generate_unique_id()
    _display_id_prefix = "AST"
    _display_id_field = "asset_id"

    # Human-readable asset ID (AST + random chars, e.g. AST7K3M9)
    # — set automatically by BaseModel.save() on first insert
    asset_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        help_text="Auto-generated HRID (e.g., AST7K3M9)",
    )

    # Organization FK — row-level isolation
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="assets",
    )

    # Category FK — optional, allows null for uncategorized assets
    category = models.ForeignKey(
        "categories.AssetCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assets",
        help_text="Asset category this asset belongs to",
    )

    # Identity
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    # Physical details
    serial_number = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Manufacturer serial / VIN number",
    )
    brand = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Brand / manufacturer name",
    )
    model_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Model name or number",
    )
    purchase_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the asset was purchased",
    )
    purchase_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Purchase price in organization's base currency",
    )
    warranty_expiry = models.DateField(
        null=True,
        blank=True,
        help_text="Warranty expiration date",
    )

    # Status — lifecycle state
    status = models.CharField(
        max_length=20,
        choices=AssetStatus.choices(),
        default=AssetStatus.AVAILABLE.value,
        help_text="Current lifecycle status of the asset",
    )

    # Assignment — which employee currently holds this asset
    assigned_to = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_assets",
        help_text="Employee this asset is currently allocated to",
    )

    # Location
    location = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Physical location or storage location of the asset",
    )

    class Meta:
        db_table = "assets"
        verbose_name = "asset"
        verbose_name_plural = "assets"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["category"]),
            models.Index(fields=["assigned_to"]),
            models.Index(fields=["status", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.asset_id})"
