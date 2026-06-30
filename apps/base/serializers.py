"""
apps/base/serializers.py — Base serializer for all AssetFlow models.

Auto-injects base model fields into every child serializer and marks them
read-only — children only declare their own unique fields.
"""

from rest_framework import serializers

from apps.base.models import BaseModel


class BaseSerializer(serializers.ModelSerializer):
    """
    Base serializer for all AssetFlow models.

    - `get_field_names()` auto-injects base fields so children only list
      their unique fields (no repetition of id, created_at, etc.)
    - `get_fields()` marks all base fields read-only automatically
    """

    class Meta:
        abstract = True
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "is_active",
            "is_deleted",
        ]

    def get_fields(self):
        """Mark all base fields read-only for all child serializers."""
        fields = super().get_fields()
        read_only = getattr(self.Meta, "read_only_fields", [])
        for field_name in read_only:
            if field_name in fields:
                fields[field_name].read_only = True
        return fields

    def get_field_names(self, declared_fields, info):
        """Inject base fields for models that inherit BaseModel.
        """
        field_names = super().get_field_names(declared_fields, info)
        if not issubclass(info.model, BaseModel):
            return field_names
        base_fields = list(getattr(self.Meta, "read_only_fields", []))
        # Append base fields so they appear last in responses
        return list(field_names) + [f for f in base_fields if f not in field_names]
