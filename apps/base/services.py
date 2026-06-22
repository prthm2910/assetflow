"""
apps/base/services.py — Bulk service for mass database operations.
"""
from django.utils import timezone


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
    def bulk_update(model, updates, user=None):
        """
        Update multiple records with individual field values.

        Args:
            model: The Django model class.
            updates: List of dicts with 'id' and field values.
            user: The user performing the update (sets updated_by).

        Returns:
            Number of records updated.
        """
        count = 0
        for item in updates:
            obj_id = item.pop('id')
            update_fields = {**item, 'updated_by': user}
            count += model.objects.filter(id=obj_id).update(**update_fields)
        return count

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
        )
