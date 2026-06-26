"""
apps/assets/requests/filters.py — FilterSet for AssetRequest.
"""

import django_filters

from apps.base.filters import BaseFilterSet
from apps.assets.requests.models import AssetRequest


class AssetRequestFilterSet(BaseFilterSet):
    """FilterSet for AssetRequest with HRID, status, and priority filters."""

    req_id = django_filters.CharFilter(
        field_name="req_id",
        label="Request HRID (e.g. REQ7K3M9)",
    )
    requested_by_id = django_filters.CharFilter(
        field_name="requested_by__emp_id",
        label="Employee HRID (e.g. EMP4X9P2)",
    )
    asset_category_id = django_filters.CharFilter(
        field_name="asset_category__id",
        label="Category UUID",
    )
    status = django_filters.CharFilter(
        field_name="status",
        label="Request status (pending, approved, rejected, fulfilled, cancelled)",
    )
    priority = django_filters.CharFilter(
        field_name="priority",
        label="Request priority (low, medium, high)",
    )

    class Meta:
        model = AssetRequest
        fields = ["req_id", "requested_by_id", "asset_category_id", "status", "priority"]
