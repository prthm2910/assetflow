"""
apps/base/managers.py — Custom model managers.

SoftDeleteManager: Filters out soft-deleted records by default.
"""
from django.db import models


class SoftDeleteManager(models.Manager):
    """
    Manager that returns only non-deleted records by default.
    Use `.all_with_deleted()` to include soft-deleted records.
    Use `.deleted_only()` to get only soft-deleted records.
    """

    def get_queryset(self):
        """Return only active (non-deleted) records."""
        return super().get_queryset().filter(is_deleted=False)

    def all_with_deleted(self):
        """Return all records including soft-deleted ones."""
        return super().get_queryset()

    def deleted_only(self):
        """Return only soft-deleted records."""
        return super().get_queryset().filter(is_deleted=True)
