"""
apps/base/managers.py — Custom model managers.

SoftDeleteManager: Filters out soft-deleted records by default, with .active() for active-only queries.
"""

from django.db import models


class ActiveQuerySetMixin:
    """Mixin adding .active() queryset method to any manager/queryset."""

    def active(self):
        """Return only active, non-deleted records."""
        return self.filter(is_deleted=False, is_active=True)


class SoftDeleteQuerySet(ActiveQuerySetMixin, models.QuerySet):
    """QuerySet with .active() method."""
    pass


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """
    Manager that returns only non-deleted records by default.

    Methods:
        .active() — only active + non-deleted records
        .all_with_deleted() — all records including soft-deleted
        .deleted_only() — only soft-deleted records
    """

    def get_queryset(self):
        """Return only non-deleted records."""
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        """Return all records including soft-deleted ones."""
        return super().get_queryset()

    def deleted_only(self):
        """Return only soft-deleted records."""
        return super().get_queryset().filter(is_deleted=True)
