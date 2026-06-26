"""
apps/assets/allocations/filters.py — FilterSet for Allocation.
"""

import django_filters

from apps.base.filters import BaseFilterSet
from apps.assets.allocations.models import Allocation


class AllocationFilterSet(BaseFilterSet):
    """FilterSet for Allocation with asset, employee, and status filters."""

    asset_id = django_filters.CharFilter(
        field_name="asset__asset_id",
        label="Asset HRID (e.g. AST7K3M9)",
    )
    employee_id = django_filters.CharFilter(
        field_name="employee__emp_id",
        label="Employee HRID (e.g. EMP4X9P2)",
    )
    is_active = django_filters.BooleanFilter(
        field_name="returned_at",
        lookup_expr="isnull",
        label="Is active (true = active, false = returned)",
    )
    status = django_filters.CharFilter(
        method="filter_status",
        label="Allocation status (active or returned)",
    )

    class Meta:
        model = Allocation
        fields = ["asset_id", "employee_id", "is_active"]

    def filter_status(self, queryset, name, value):
        if value == "active":
            return queryset.filter(returned_at__isnull=True)
        if value == "returned":
            return queryset.filter(returned_at__isnull=False)
        return queryset
