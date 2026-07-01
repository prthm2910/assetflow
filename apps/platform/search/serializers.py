"""
apps/platform/search/serializers.py — Minimal serializers for global search results.

Each serializer exposes just enough fields for a search result card.
The user clicks through to the full detail view via view_all_url.
"""

from rest_framework import serializers


class AssetSearchSerializer(serializers.Serializer):
    """Minimal asset info for search results."""

    asset_id = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    category_name = serializers.CharField(read_only=True)


class EmployeeSearchSerializer(serializers.Serializer):
    """Minimal employee info for search results."""

    employee_id = serializers.CharField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    email = serializers.CharField(read_only=True)
    designation = serializers.CharField(read_only=True)
    department_name = serializers.CharField(read_only=True, allow_null=True)


class RequestSearchSerializer(serializers.Serializer):
    """Minimal asset request info for search results."""

    req_id = serializers.CharField(read_only=True)
    reason = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    priority = serializers.CharField(read_only=True)
    requested_by_name = serializers.CharField(read_only=True, allow_null=True)


class IncidentSearchSerializer(serializers.Serializer):
    """Minimal incident info for search results."""

    inc_id = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    reported_by_name = serializers.CharField(read_only=True, allow_null=True)


class LicenseSearchSerializer(serializers.Serializer):
    """Minimal license info for search results."""

    lic_id = serializers.CharField(read_only=True)
    software_name = serializers.CharField(read_only=True)
    license_type = serializers.CharField(read_only=True)
    total_seats = serializers.IntegerField(read_only=True)
    used_seats = serializers.IntegerField(read_only=True)
    available_seats = serializers.IntegerField(read_only=True)
    expiry_date = serializers.DateField(read_only=True, allow_null=True)
