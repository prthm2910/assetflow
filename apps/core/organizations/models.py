"""
apps/core/organizations/models.py — Organization and OrganizationConfig models.
"""

from datetime import time, timezone as dt_tz

from django.conf import settings
from django.db import models

from apps.base.models import BaseModel


class Organization(BaseModel):
    """
    Organization model — top-level tenant in multi-tenant architecture.

    Inherits from BaseModel:
    - UUID primary key
    - created_at / updated_at / created_by / updated_by
    - is_active, is_deleted, deleted_at (soft delete)
    - Auto HRID via BaseModel.save() — sets _display_id_prefix + _display_id_field
    """

    _display_id_prefix = "ORG"
    _display_id_field = "org_id"

    # HRID — public API identifier (e.g., ORG7K3M9)
    org_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        help_text="Human-readable unique ID (auto-generated)",
    )

    # Core identity
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, help_text="URL-safe identifier")
    description = models.TextField(blank=True, default="")

    # Contact
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=30, blank=True, default="")
    address = models.TextField(blank=True, default="")
    city = models.CharField(max_length=100, blank=True, default="")
    country = models.CharField(max_length=100, blank=True, default="")

    # Logo upload
    logo = models.ImageField(
        upload_to="org_logos/",
        blank=True,
        null=True,
        help_text="Organization logo image",
    )

    class Meta:
        db_table = "organizations"
        verbose_name = "organization"
        verbose_name_plural = "organizations"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.org_id})"

    def save(self, *args, **kwargs):
        """Auto-generate org_id via BaseModel and ensure config exists on first save."""
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not hasattr(self, "config"):
            OrganizationConfig.objects.create(organization=self)

    def get_admin_user(self):
        """Return the designated admin user for this organization."""
        config = getattr(self, "config", None)
        if config and config.admin_user_id:
            try:
                return settings.AUTH_USER_MODEL.objects.get(id=config.admin_user_id)
            except settings.AUTH_USER_MODEL.DoesNotExist:
                return None
        return None


class OrganizationConfig(BaseModel):
    """
    Organization-level configuration and preferences.

    OneToOne with Organization — each org has exactly one config.
    Inherits from BaseModel for audit fields and soft delete.
    No HRID — _display_id_field stays None so BaseModel.save() skips generation.
    """

    # Link back to organization
    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name="config",
    )

    # Admin user — designated primary admin for this org
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="administered_organizations",
        help_text="Primary admin user for this organization",
    )

    # Timezone & working hours
    default_timezone = models.CharField(
        max_length=63,
        default="UTC",
        help_text="IANA timezone string (e.g., Asia/Kolkata)",
    )
    working_hours_start = models.TimeField(
        default=time(hour=9, minute=0, tzinfo=dt_tz.utc),
        help_text="Start of working day (HH:MM)",
    )
    working_hours_end = models.TimeField(
        default=time(hour=18, minute=0, tzinfo=dt_tz.utc),
        help_text="End of working day (HH:MM)",
    )
    working_days = models.JSONField(
        default=list,
        blank=True,
        help_text="List of weekdays as integers 0–6 (0=Monday). E.g., [0,1,2,3,4] for Mon–Fri.",
    )

    # Asset code prefix (e.g., "ACME" → ACME-2026-00001)
    asset_code_prefix = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Prefix for auto-generated asset codes",
    )

    # Workflow flags
    request_approval_required = models.BooleanField(
        default=True,
        help_text="Whether asset requests need org admin approval",
    )
    auto_approve_requests = models.BooleanField(
        default=False,
        help_text="Auto-approve requests up to this count per employee per month",
    )
    max_requests_per_month = models.PositiveIntegerField(
        default=0,
        help_text="Max requests per employee per month (0 = unlimited, only if auto_approve is on)",
    )

    # Notification flags
    notify_on_asset_allocated = models.BooleanField(default=True)
    notify_on_asset_returned = models.BooleanField(default=True)
    notify_on_request_submitted = models.BooleanField(default=True)
    notify_on_request_approved = models.BooleanField(default=True)
    notify_on_request_rejected = models.BooleanField(default=True)
    notify_on_incident_reported = models.BooleanField(default=True)
    notify_on_incident_resolved = models.BooleanField(default=True)

    class Meta:
        db_table = "organization_configs"
        verbose_name = "organization config"
        verbose_name_plural = "organization configs"

    def __str__(self):
        return f"Config for {self.organization.name}"

    def save(self, *args, **kwargs):
        if not self.working_days:
            self.working_days = [0, 1, 2, 3, 4]  # Mon–Fri
        super().save(*args, **kwargs)
