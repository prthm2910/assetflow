"""
apps/assets/inventory/filters.py — FilterSet for Asset.
"""

import django_filters

from apps.base.filters import BaseFilterSet
from apps.assets.inventory.models import Asset


class AssetFilterSet(BaseFilterSet):
    """FilterSet for Asset with status, name, and category filters."""

    status = django_filters.CharFilter(
        field_name="status",
        label="Asset status (e.g. available, allocated, maintenance)",
    )
    category = django_filters.UUIDFilter(
        field_name="category__id",
        label="Category UUID",
    )
    brand = django_filters.CharFilter(
        field_name="brand",
        lookup_expr="icontains",
        label="Brand contains",
    )
    assigned_to = django_filters.UUIDFilter(
        field_name="assigned_to__id",
        label="Assigned employee UUID",
    )

    class Meta:
        model = Asset
        fields = ["status", "is_active", "category", "brand", "assigned_to"]
