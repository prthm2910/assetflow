"""
apps/base/models.py — Base model for all AssetFlow models.

Provides UUID primary key, audit fields, soft delete, and auto-HRID generation.
"""

import logging
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.base.managers import SoftDeleteManager

logger = logging.getLogger(__name__)


class BaseModel(models.Model):
    """
    Abstract base model with:
    - UUID primary key (prevents ID enumeration attacks)
    - created_at / updated_at timestamps
    - created_by / updated_by audit FKs
    - is_active / is_deleted soft delete flags
    - Auto HRID generation (subclasses set _display_id_prefix and _display_id_field)

    Subclasses must define:
        _display_id_prefix = 'AST'  # e.g., 'AST', 'EMP', 'REQ'
        _display_id_field = 'asset_id'  # MUST match the actual CharField name
    """

    # UUID primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_%(class)s_set",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_%(class)s_set",
    )

    # Soft delete + active toggle
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Display ID config — child classes set these
    _display_id_prefix = None  # e.g., 'AST', 'EMP', 'REQ'
    _display_id_field = None  # MUST match the CharField name on the model

    # Default manager (excludes soft-deleted)
    objects = SoftDeleteManager()
    all_objects = models.Manager()  # Includes soft-deleted

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Auto-generate display ID if configured and field is empty."""
        if self._display_id_prefix and self._display_id_field:
            if not getattr(self, self._display_id_field, None):
                from apps.base.utils import generate_unique_id

                new_id = generate_unique_id(
                    model_class=self.__class__,
                    field_name=self._display_id_field,
                    prefix=self._display_id_prefix,
                    length=6,
                )
                setattr(self, self._display_id_field, new_id)
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """Soft-delete — sets flags and deleted_at timestamp."""
        self.is_deleted = True
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "is_active", "deleted_at", "updated_at"])
        logger.debug("Soft-deleted %s pk=%s", self.__class__.__name__, self.pk)

    def hard_delete(self, using=None, keep_parents=False):
        """Actual database delete (bypasses soft delete)."""
        logger.warning("Hard-deleting %s pk=%s", self.__class__.__name__, self.pk)
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restore a soft-deleted object."""
        self.is_deleted = False
        self.is_active = True
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "is_active", "deleted_at", "updated_at"])
        logger.info("Restored %s pk=%s", self.__class__.__name__, self.pk)

