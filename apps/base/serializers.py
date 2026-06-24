"""
apps/base/serializers.py — Base serializer and timezone-aware mixin.

All AssetFlow serializers inherit from BaseSerializer which provides:
- All BaseModel fields as read-only
- Timezone conversion for datetime fields
"""
from datetime import datetime
from rest_framework import serializers
from django.utils import timezone
from django.utils.dateparse import parse_datetime


class TimezoneAwareSerializerMixin:
    """
    Converts UTC datetime fields to the requesting user's timezone on output.

    Usage:
        class AssetSerializer(TimezoneAwareSerializerMixin, serializers.ModelSerializer):
            ...
    """

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')

        if not request or not hasattr(request, 'user'):
            return data

        user = request.user
        if not user or not user.is_authenticated:
            return data

        user_tz_name = getattr(user, 'timezone', 'UTC')
        if user_tz_name == 'UTC':
            return data

        try:
            import pytz
            user_tz = pytz.timezone(user_tz_name)

            for field_name, value in data.items():
                if value is None:
                    continue
                if isinstance(value, datetime):
                    if timezone.is_aware(value):
                        data[field_name] = timezone.localtime(value, user_tz)
                    elif isinstance(value, str):
                        parsed = parse_datetime(value)
                        if parsed and timezone.is_aware(parsed):
                            data[field_name] = timezone.localtime(parsed, user_tz)
        except Exception:
            # If timezone conversion fails, return data as-is
            pass

        return data


class BaseSerializer(TimezoneAwareSerializerMixin, serializers.ModelSerializer):
    """
    Base serializer for all AssetFlow models.

    Includes all BaseModel fields as read-only.
    Child serializers extend Meta.fields with their own fields.
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
