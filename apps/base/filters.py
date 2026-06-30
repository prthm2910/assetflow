"""
apps/base/filters.py — Reusable Django Filter FilterSet classes.
"""

import django_filters


class BaseFilterSet(django_filters.FilterSet):
    """
    Base FilterSet with common filters for all models.
    """

    created_after = django_filters.IsoDateTimeFilter(
        field_name="created_at",
        lookup_expr="gte",
        label="Created after (ISO format)",
    )
    created_before = django_filters.IsoDateTimeFilter(
        field_name="created_at",
        lookup_expr="lte",
        label="Created before (ISO format)",
    )
    is_active = django_filters.BooleanFilter(
        field_name="is_active",
        label="Is active",
    )
    is_deleted = django_filters.BooleanFilter(
        field_name="is_deleted",
        label="Is deleted",
    )
