"""
apps/base/services.py — Bulk service for mass database operations.
"""

from django.utils import timezone
from django.db import transaction


class BulkService:
    """
    Handles bulk database operations efficiently.

    Uses Django ORM's bulk operations for performance where possible.
    """

    @staticmethod
    def bulk_create(serializer_class, validated_data, context):
        """
        Validate and create multiple objects via serializer.

        Args:
            serializer_class: The serializer class to use for validation.
            validated_data: List of validated data dicts.
            context: Serializer context (request, etc.).

        Returns:
            List of created model instances.
        """
        serializer = serializer_class(data=validated_data, many=True, context=context)
        serializer.is_valid(raise_exception=True)
        return serializer.save()

    @staticmethod
    def bulk_update(queryset, updates, user=None):
        """
        Update multiple records efficiently using Django's bulk_update().

        Generates a single SQL UPDATE with CASE WHEN instead of N individual
        UPDATE queries. All updates run inside a transaction.

        Args:
            queryset: The Django QuerySet to update.
            updates: List of dicts with 'id' and field values.
            user: The user performing the update (sets updated_by).

        Returns:
            Number of records updated.
        """

        if not updates:
            return 0

        with transaction.atomic():
            # Build model instances from update dicts
            objs = []
            fields_to_update = set()
            for item in updates:
                obj_id = item.pop("id", None)
                if not obj_id:
                    continue
                try:
                    obj = queryset.get(id=obj_id)
                except queryset.model.DoesNotExist:
                    continue
                for field, value in item.items():
                    setattr(obj, field, value)
                    fields_to_update.add(field)
                if user:
                    obj.updated_by = user
                    fields_to_update.add("updated_by")
                obj.updated_at = timezone.now()
                fields_to_update.add("updated_at")
                objs.append(obj)

            if not objs:
                return 0

            return queryset.model.objects.bulk_update(
                objs, fields=list(fields_to_update)
            )

    @staticmethod
    def bulk_soft_delete(queryset):
        """
        Soft-delete all records in the queryset.

        Args:
            queryset: Django QuerySet to soft-delete.

        Returns:
            Number of records soft-deleted.
        """
        return queryset.update(
            is_deleted=True,
            is_active=False,
            deleted_at=timezone.now(),
            updated_at=timezone.now(),
        )
