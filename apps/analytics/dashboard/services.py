"""
apps/analytics/dashboard/services.py — Repository classes for Dashboard aggregation.

Each Repository encapsulates queries for one model, returning clean dicts
for the dashboard views.

Usage:
    >>> from apps.analytics.dashboard.services import AssetRepository
    >>> data = AssetRepository.get_status_breakdown(organization)
    >>> data
    [{"status": "available", "count": 12}, {"status": "allocated", "count": 8}]
"""

from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone

from apps.assets.allocations.models import Allocation
from apps.assets.inventory.models import Asset
from apps.assets.inventory.constants import AssetStatus
from apps.assets.requests.models import AssetRequest
from apps.assets.requests.constants import RequestStatus
from apps.core.employees.models import Employee
from apps.operations.incidents.models import Incident
from apps.operations.incidents.constants import IncidentStatus
from apps.operations.licenses.models import SoftwareLicense


# ==============================================================================
# Base Repository
# ==============================================================================

class BaseRepository:
    """Common aggregation helpers for all dashboard repositories.

    Subclasses set ``model`` and may override ``org_queryset`` if the
    model uses a different soft-delete or scoping convention.
    """

    model = None

    @classmethod
    def org_queryset(cls, organization):
        """Return a base queryset scoped to *organization*, excluding soft-deleted rows."""
        return cls.model.objects.filter(organization=organization, is_deleted=False)

    @classmethod
    def get_total_count(cls, organization):
        """Total non-deleted records for *organization*."""
        return cls.org_queryset(organization).count()


# ==============================================================================
# Asset Repository
# ==============================================================================

class AssetRepository(BaseRepository):
    """Aggregation queries for the Asset model."""

    model = Asset

    @classmethod
    def get_status_breakdown(cls, organization):
        """Count of assets grouped by status.

        Returns:
            list[dict]: ``[{"status": "available", "count": 12}, …]``
        """
        qs = (
            cls.org_queryset(organization)
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        return list(qs)

    @classmethod
    def get_category_breakdown(cls, organization):
        """Count of assets grouped by category name.

        Returns:
            list[dict]: ``[{"name": "Electronics", "count": 5}, …]``
        """
        qs = (
            cls.org_queryset(organization)
            .values("category__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return [
            {"name": item["category__name"], "count": item["count"]}
            for item in qs
            if item["category__name"] is not None
        ]

    @classmethod
    def get_allocated_count(cls, organization):
        """Number of assets currently in 'allocated' status."""
        return cls.org_queryset(organization).filter(
            status=AssetStatus.ALLOCATED.value
        ).count()

    @classmethod
    def get_available_count(cls, organization):
        """Number of assets currently in 'available' status."""
        return cls.org_queryset(organization).filter(
            status=AssetStatus.AVAILABLE.value
        ).count()

    @classmethod
    def get_utilization_rate(cls, organization):
        """Percentage of assets that are allocated."""
        total = cls.get_total_count(organization)
        if total == 0:
            return 0.0
        allocated = cls.get_allocated_count(organization)
        return round((allocated / total) * 100, 1)


# ==============================================================================
# Incident Repository
# ==============================================================================

class IncidentRepository(BaseRepository):
    """Aggregation queries for the Incident model."""

    model = Incident

    @classmethod
    def get_status_breakdown(cls, organization):
        """Count of incidents grouped by status."""
        qs = (
            cls.org_queryset(organization)
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        return list(qs)

    @classmethod
    def get_category_breakdown(cls, organization):
        """Count of incidents grouped by category."""
        qs = (
            cls.org_queryset(organization)
            .values("category")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return list(qs)

    @classmethod
    def get_open_count(cls, organization):
        """Incidents that are not yet resolved or closed."""
        return cls.org_queryset(organization).exclude(
            status__in=[IncidentStatus.RESOLVED.value, IncidentStatus.CLOSED.value]
        ).count()

    @classmethod
    def get_resolved_count(cls, organization):
        """Incidents that are resolved or closed."""
        return cls.org_queryset(organization).filter(
            status__in=[IncidentStatus.RESOLVED.value, IncidentStatus.CLOSED.value]
        ).count()


# ==============================================================================
# Request Repository
# ==============================================================================

class RequestRepository(BaseRepository):
    """Aggregation queries for the AssetRequest model."""

    model = AssetRequest

    @classmethod
    def get_status_breakdown(cls, organization):
        """Count of requests grouped by status."""
        qs = (
            cls.org_queryset(organization)
            .values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        return list(qs)

    @classmethod
    def get_pending_count(cls, organization):
        """Requests awaiting review."""
        return cls.org_queryset(organization).filter(
            status=RequestStatus.PENDING.value
        ).count()

    @classmethod
    def get_approved_count(cls, organization):
        """Approved requests."""
        return cls.org_queryset(organization).filter(
            status=RequestStatus.APPROVED.value
        ).count()

    @classmethod
    def get_rejected_count(cls, organization):
        """Rejected requests."""
        return cls.org_queryset(organization).filter(
            status=RequestStatus.REJECTED.value
        ).count()


# ==============================================================================
# License Repository
# ==============================================================================

class LicenseRepository(BaseRepository):
    """Aggregation queries for the SoftwareLicense model."""

    model = SoftwareLicense

    @classmethod
    def get_type_breakdown(cls, organization):
        """Count of licenses grouped by license_type."""
        qs = (
            cls.org_queryset(organization)
            .values("license_type")
            .annotate(count=Count("id"))
            .order_by("license_type")
        )
        return list(qs)

    @classmethod
    def get_total_seats(cls, organization):
        """Sum of total_seats across all licenses."""
        result = cls.org_queryset(organization).aggregate(total=Sum("total_seats"))
        return result["total"] or 0

    @classmethod
    def get_used_seats(cls, organization):
        """Sum of active (non-revoked) assignment counts across all licenses.

        Queries LicenseAssignment directly, scoped to the organization's
        licenses, counting only assignments that have not been revoked.
        """
        from apps.operations.licenses.models import LicenseAssignment

        result = LicenseAssignment.objects.filter(
            license__organization=organization,
            license__is_deleted=False,
            revoked_at__isnull=True,
        ).count()
        return result

    @classmethod
    def get_license_utilization_rate(cls, organization):
        """Percentage of total seats that are currently assigned."""
        total = cls.get_total_seats(organization)
        if total == 0:
            return 0.0
        used = cls.get_used_seats(organization)
        return round((used / total) * 100, 1)

    @classmethod
    def get_expiring_soon(cls, organization, days=30):
        """Licenses expiring within *days* from now (excluding already expired)."""
        now = timezone.now()
        cutoff = now + timedelta(days=days)
        return cls.org_queryset(organization).filter(
            expiry_date__gte=now.date(),
            expiry_date__lte=cutoff.date(),
            expiry_date__isnull=False,
        ).count()


# ==============================================================================
# Allocation Repository
# ==============================================================================

class AllocationRepository(BaseRepository):
    """Aggregation queries for the Allocation model."""

    model = Allocation

    @classmethod
    def get_active_count(cls, organization):
        """Allocations that have not been returned."""
        return cls.org_queryset(organization).filter(returned_at__isnull=True).count()

    @classmethod
    def get_returned_count(cls, organization):
        """Allocations that have been returned."""
        return cls.org_queryset(organization).filter(returned_at__isnull=False).count()


# ==============================================================================
# Employee Repository (lightweight, for summary only)
# ==============================================================================

class EmployeeRepository(BaseRepository):
    """Aggregation queries for the Employee model."""

    model = Employee

    @classmethod
    def get_department_breakdown(cls, organization):
        """Count of employees grouped by department name."""
        qs = (
            cls.org_queryset(organization)
            .values("department__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return [
            {"name": item["department__name"], "count": item["count"]}
            for item in qs
            if item["department__name"] is not None
        ]


# ==============================================================================
# Summary — single call, all stats
# ==============================================================================

class DashboardSummaryService:
    """Aggregates stats across all modules in one place.

    Usage:
        >>> summary = DashboardSummaryService.get_summary(organization)
        >>> summary["assets"]["total"]
        42
    """

    @staticmethod
    def get_summary(organization):
        """Return a dict of high-level stats for every module."""
        return {
            "assets": {
                "total": AssetRepository.get_total_count(organization),
                "allocated": AssetRepository.get_allocated_count(organization),
                "available": AssetRepository.get_available_count(organization),
                "utilization_rate": AssetRepository.get_utilization_rate(organization),
            },
            "incidents": {
                "total": IncidentRepository.get_total_count(organization),
                "open": IncidentRepository.get_open_count(organization),
                "resolved": IncidentRepository.get_resolved_count(organization),
            },
            "requests": {
                "total": RequestRepository.get_total_count(organization),
                "pending": RequestRepository.get_pending_count(organization),
                "approved": RequestRepository.get_approved_count(organization),
                "rejected": RequestRepository.get_rejected_count(organization),
            },
            "licenses": {
                "total": LicenseRepository.get_total_count(organization),
                "total_seats": LicenseRepository.get_total_seats(organization),
                "used_seats": LicenseRepository.get_used_seats(organization),
                "utilization_rate": LicenseRepository.get_license_utilization_rate(organization),
                "expiring_soon": LicenseRepository.get_expiring_soon(organization),
            },
            "allocations": {
                "total": AllocationRepository.get_total_count(organization),
                "active": AllocationRepository.get_active_count(organization),
                "returned": AllocationRepository.get_returned_count(organization),
            },
            "employees": {
                "total": EmployeeRepository.get_total_count(organization),
            },
        }
