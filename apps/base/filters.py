"""
apps/base/filters.py — Reusable Django Filter FilterSet classes.
"""
import django_filters
from django import forms


class BaseFilterSet(django_filters.FilterSet):
    """
    Base FilterSet with common filters for all models.
    """

    created_after = django_filters.IsoDateTimeFilter(
        field_name='created_at',
        lookup_expr='gte',
        label='Created after (ISO format)',
    )
    created_before = django_filters.IsoDateTimeFilter(
        field_name='created_at',
        lookup_expr='lte',
        label='Created before (ISO format)',
    )
    is_active = django_filters.BooleanFilter(
        field_name='is_active',
        label='Is active',
    )
    is_deleted = django_filters.BooleanFilter(
        field_name='is_deleted',
        label='Is deleted',
    )


class NameFilter(django_filters.FilterSet):
    """
    FilterSet with name search (icontains).
    """

    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        label='Name contains',
    )


class SoftDeleteFilterSet(BaseFilterSet):
    """
    FilterSet that excludes soft-deleted records by default.
    Include ?include_deleted=true to show deleted records.
    """

    include_deleted = django_filters.BooleanFilter(
        method='filter_include_deleted',
        label='Include deleted records',
    )

    class Meta:
        abstract = True

    def filter_include_deleted(self, queryset, name, value):
        if value:
            return getattr(queryset.model, 'all_objects', queryset).all()
        return queryset
