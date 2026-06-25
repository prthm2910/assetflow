"""
apps/assets/categories/models.py — Asset Category model.
"""

from django.db import models

from apps.base.models import BaseModel


class AssetCategory(BaseModel):
    """
    Asset category with optional parent hierarchy (sub-categories).

    Inherits from BaseModel:
    - UUID primary key, org FK, created_at / updated_at / created_by / updated_by
    - is_active, is_deleted, deleted_at (soft delete)
    - Auto HRID via BaseModel.save()
    """

    _display_id_prefix = "CAT"
    _display_id_field = "cat_id"

    # HRID — public API identifier (e.g., CAT7K3M9)
    cat_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        help_text="Human-readable unique ID (auto-generated)",
    )

    # Organization FK — row-level isolation
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="asset_categories",
    )

    # Category identity
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    # Parent hierarchy — a category can have a parent category (sub-category)
    parent = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="sub_categories",
        help_text="Parent category. Leave blank to create a top-level category.",
    )

    class Meta:
        db_table = "asset_categories"
        verbose_name = "asset category"
        verbose_name_plural = "asset categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                condition=models.Q(is_deleted=False),
                name="unique_active_category_name_per_org",
            )
        ]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.cat_id})"
