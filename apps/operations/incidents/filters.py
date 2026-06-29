"""apps/operations/incidents/filters.py — FilterSet for Incident."""

import django_filters

from apps.base.filters import BaseFilterSet
from apps.operations.incidents.models import Incident


class IncidentFilterSet(BaseFilterSet):
    """FilterSet for Incident with HRID, status, category, and related filters."""

    inc_id = django_filters.CharFilter(
        field_name="inc_id",
        label="Incident HRID (e.g. INC7K3M9)",
    )
    asset_id = django_filters.CharFilter(
        field_name="asset__asset_id",
        label="Asset HRID (e.g. AST7K3M9)",
    )
    reported_by_id = django_filters.CharFilter(
        field_name="reported_by__emp_id",
        label="Reporter Employee HRID (e.g. EMP4X9P2)",
    )
    status = django_filters.CharFilter(
        field_name="status",
        label="Incident status (reported, open, in_progress, resolved, closed)",
    )
    category = django_filters.CharFilter(
        field_name="category",
        label="Incident category (hardware, software, physical_damage, performance, other)",
    )

    class Meta:
        model = Incident
        fields = ["inc_id", "asset_id", "reported_by_id", "status", "category"]
