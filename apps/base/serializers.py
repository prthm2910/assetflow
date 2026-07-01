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

    - ``BASE_READ_ONLY_FIELDS``: a class-level constant listing the
      ``BaseModel`` fields that every child serializer inherits.
    - ``get_field_names()`` auto-injects these fields so children only list
      their unique fields (no repetition of ``id``, ``created_at``, etc.).
    - ``get_fields()`` marks all base fields as read-only automatically.

    Child serializers define their own ``Meta`` and only need to list their
    unique fields — the base fields are injected automatically:

    .. code-block:: python

        class AssetSerializer(BaseSerializer):
            class Meta:
                model = Asset
                fields = ['asset_id', 'name', 'status', ...]

    See ``docs/guides/base-serializer-pattern.md`` for the full rationale.
    """

    BASE_READ_ONLY_FIELDS = [
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "is_active",
        "is_deleted",
    ]

    class Meta:
        abstract = True

    def get_fields(self):
        """Mark all base fields read-only for all child serializers."""
        fields = super().get_fields()
        for field_name in self.BASE_READ_ONLY_FIELDS:
            if field_name in fields:
                fields[field_name].read_only = True
        child_read_only = getattr(self.Meta, "read_only_fields", [])
        for field_name in child_read_only:
            if field_name in fields:
                fields[field_name].read_only = True
        return fields

    def get_field_names(self, declared_fields, info):
        """Inject base fields for models that inherit BaseModel."""
        field_names = super().get_field_names(declared_fields, info)
        model = getattr(self.Meta, "model", None)
        if model is None or not issubclass(model, BaseModel):
            return field_names
        return list(field_names) + [f for f in self.BASE_READ_ONLY_FIELDS if f not in field_names]
