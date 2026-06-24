"""
apps/base/serializers.py — Base serializer for all AssetFlow models.

All serializers inherit from BaseSerializer which provides:
- All BaseModel fields as read-only
"""

from rest_framework import serializers


class BaseSerializer(serializers.ModelSerializer):
    """
    Base serializer for all AssetFlow models.

    Includes all BaseModel fields as read-only.
    Child serializers extend Meta.fields with their own fields.

    Note: All datetime values are returned in UTC. Clients should handle
    timezone conversion locally based on user preferences.
    """

    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    updated_by = serializers.PrimaryKeyRelatedField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    is_deleted = serializers.BooleanField(read_only=True)
    deleted_at = serializers.DateTimeField(read_only=True)

    class Meta:
        abstract = True
