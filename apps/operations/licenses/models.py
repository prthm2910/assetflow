"""apps/operations/licenses/models.py — Software license management."""

from django.db import models

from apps.base.models import BaseModel
from apps.operations.licenses.constants import LicenseType


class SoftwareLicense(BaseModel):
    """
    Tracks software licenses owned by an organization.

    Inherits from BaseModel:
    - UUID primary key, org FK, created_at / updated_at / created_by / updated_by
    - is_active, is_deleted (soft delete)
    - Auto HRID generation via _display_id_prefix / _display_id_field
    """

    _display_id_prefix = "LIC"
    _display_id_field = "lic_id"

    lic_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        help_text="Auto-generated HRID (e.g., LIC7K3M9)",
    )

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="software_licenses",
    )

    software_name = models.CharField(
        max_length=255,
        help_text="Name of the software",
    )

    license_key = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text="License key or activation code",
    )

    license_type = models.CharField(
        max_length=20,
        choices=LicenseType.choices(),
        help_text="License type (per_user, per_device, site)",
    )

    total_seats = models.PositiveIntegerField(
        help_text="Total number of available seats",
    )

    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text="License expiry date",
    )

    purchase_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Purchase cost",
    )

    vendor = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Software vendor",
    )

    document = models.FileField(
        upload_to="licenses/docs/",
        null=True,
        blank=True,
        help_text="License document or receipt",
    )

    class Meta:
        db_table = "software_licenses"
        verbose_name = "software license"
        verbose_name_plural = "software licenses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "license_type"]),
            models.Index(fields=["expiry_date"]),
        ]

    def __str__(self):
        return f"{self.software_name} ({self.lic_id})"

    @property
    def used_seats(self):
        """Count of active (non-revoked) assignments."""
        return self.assignments.filter(revoked_at__isnull=True).count()

    @property
    def available_seats(self):
        """Remaining available seats."""
        return max(0, self.total_seats - self.used_seats)


class LicenseAssignment(BaseModel):
    """
    Tracks assignment of a license seat to an employee and/or asset.

    Either employee or asset (or both) must be set.
    revoking sets revoked_at — does not soft-delete.
    """

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="license_assignments",
    )

    license = models.ForeignKey(
        "licenses.SoftwareLicense",
        on_delete=models.CASCADE,
        related_name="assignments",
    )

    employee = models.ForeignKey(
        "employees.Employee",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="license_assignments",
        help_text="Employee assigned this license",
    )

    asset = models.ForeignKey(
        "inventory.Asset",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="license_assignments",
        help_text="Asset assigned this license",
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this assignment was revoked",
    )

    class Meta:
        db_table = "license_assignments"
        verbose_name = "license assignment"
        verbose_name_plural = "license assignments"
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["license", "revoked_at"]),
            models.Index(fields=["employee"]),
            models.Index(fields=["asset"]),
        ]

    def __str__(self):
        target = "Unknown"
        if self.employee and getattr(self.employee, "user", None):
            target = self.employee.user.get_full_name()
        elif self.asset:
            target = self.asset.name
        return f"{self.license.software_name} → {target} ({self.id})"

    @property
    def is_active(self):
        """True when the assignment has not been revoked."""
        return self.revoked_at is None
