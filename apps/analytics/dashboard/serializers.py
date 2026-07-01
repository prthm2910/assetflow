"""
apps/analytics/dashboard/serializers.py — Serializers for dashboard endpoints.

These are read-only serializers that document the dashboard response
structures for drf-spectacular (OpenAPI schema generation).
"""

from rest_framework import serializers


class StatusBreakdownItemSerializer(serializers.Serializer):
    """A single status-count pair."""

    status = serializers.CharField(read_only=True)
    count = serializers.IntegerField(read_only=True)


class CategoryBreakdownItemSerializer(serializers.Serializer):
    """A single category-count pair."""

    name = serializers.CharField(read_only=True)
    count = serializers.IntegerField(read_only=True)


class LicenseTypeBreakdownItemSerializer(serializers.Serializer):
    """A single license-type-count pair."""

    license_type = serializers.CharField(read_only=True)
    count = serializers.IntegerField(read_only=True)


class EmployeeSummarySerializer(serializers.Serializer):
    """Employee summary — just total count."""

    total = serializers.IntegerField(read_only=True)


class AssetSummarySerializer(serializers.Serializer):
    """High-level asset stats for the summary endpoint."""

    total = serializers.IntegerField(read_only=True)
    allocated = serializers.IntegerField(read_only=True)
    available = serializers.IntegerField(read_only=True)
    utilization_rate = serializers.FloatField(read_only=True)


class IncidentSummarySerializer(serializers.Serializer):
    """High-level incident stats."""

    total = serializers.IntegerField(read_only=True)
    open = serializers.IntegerField(read_only=True)
    resolved = serializers.IntegerField(read_only=True)


class RequestSummarySerializer(serializers.Serializer):
    """High-level request stats."""

    total = serializers.IntegerField(read_only=True)
    pending = serializers.IntegerField(read_only=True)
    approved = serializers.IntegerField(read_only=True)
    rejected = serializers.IntegerField(read_only=True)


class LicenseSummarySerializer(serializers.Serializer):
    """High-level license stats."""

    total = serializers.IntegerField(read_only=True)
    total_seats = serializers.IntegerField(read_only=True)
    used_seats = serializers.IntegerField(read_only=True)
    utilization_rate = serializers.FloatField(read_only=True)
    expiring_soon = serializers.IntegerField(read_only=True)


class AllocationSummarySerializer(serializers.Serializer):
    """High-level allocation stats."""

    total = serializers.IntegerField(read_only=True)
    active = serializers.IntegerField(read_only=True)
    returned = serializers.IntegerField(read_only=True)


class DashboardSummarySerializer(serializers.Serializer):
    """Aggregated stats across all modules."""

    assets = AssetSummarySerializer(read_only=True)
    incidents = IncidentSummarySerializer(read_only=True)
    requests = RequestSummarySerializer(read_only=True)
    licenses = LicenseSummarySerializer(read_only=True)
    allocations = AllocationSummarySerializer(read_only=True)
    employees = EmployeeSummarySerializer(read_only=True)


class AssetDashboardSerializer(serializers.Serializer):
    """Asset-specific dashboard data."""

    total_assets = serializers.IntegerField(read_only=True)
    status_breakdown = StatusBreakdownItemSerializer(many=True, read_only=True)
    category_breakdown = CategoryBreakdownItemSerializer(many=True, read_only=True)
    utilization_rate = serializers.FloatField(read_only=True)


class IncidentDashboardSerializer(serializers.Serializer):
    """Incident-specific dashboard data."""

    total_incidents = serializers.IntegerField(read_only=True)
    status_breakdown = StatusBreakdownItemSerializer(many=True, read_only=True)
    category_breakdown = StatusBreakdownItemSerializer(many=True, read_only=True)


class RequestDashboardSerializer(serializers.Serializer):
    """Request-specific dashboard data."""

    total_requests = serializers.IntegerField(read_only=True)
    status_breakdown = StatusBreakdownItemSerializer(many=True, read_only=True)


class LicenseDashboardSerializer(serializers.Serializer):
    """License-specific dashboard data."""

    total_licenses = serializers.IntegerField(read_only=True)
    type_breakdown = LicenseTypeBreakdownItemSerializer(many=True, read_only=True)
    total_seats = serializers.IntegerField(read_only=True)
    used_seats = serializers.IntegerField(read_only=True)
    utilization_rate = serializers.FloatField(read_only=True)
    expiring_soon = serializers.IntegerField(read_only=True)


class AllocationDashboardSerializer(serializers.Serializer):
    """Allocation-specific dashboard data."""

    total_allocations = serializers.IntegerField(read_only=True)
    active = serializers.IntegerField(read_only=True)
    returned = serializers.IntegerField(read_only=True)
