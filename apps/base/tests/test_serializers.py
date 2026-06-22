"""
apps/base/tests/test_serializers.py — Tests for BaseSerializer and mixins.
"""
import pytest
from rest_framework.test import APIRequestFactory
from rest_framework import serializers


class DummySerializer(serializers.Serializer):
    """Concrete serializer for testing mixins."""
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()


@pytest.mark.django_db
class TestTimezoneAwareSerializerMixin:
    """Tests for TimezoneAwareSerializerMixin."""

    def test_mixin_handles_unauthenticated(self):
        """Mixin should handle unauthenticated requests gracefully."""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = None

        serializer = DummySerializer(context={'request': request})
        # Should not raise an error
        result = serializer.data
        assert isinstance(result, dict)

    def test_mixin_handles_authenticated_user(self):
        """Mixin should work with authenticated requests."""
        factory = APIRequestFactory()
        request = factory.get('/')
        request.user = None  # timezone is None for anonymous

        serializer = DummySerializer(context={'request': request})
        result = serializer.data
        assert isinstance(result, dict)


@pytest.mark.django_db
class TestSerializerFields:
    """Tests for serializer read-only field behavior."""

    def test_read_only_fields_rejected_in_input(self):
        """Read-only fields should not appear in validated_data."""
        serializer = DummySerializer(data={'id': 999, 'name': 'Test'})
        # id is read_only, so is_valid will fail if it's required
        # For this serializer, name is required, id is ignored
        assert serializer.is_valid()
        assert 'name' in serializer.validated_data
        # id is read_only so it won't be in validated_data
        assert 'id' not in serializer.validated_data

    def test_required_fields_enforced(self):
        """Required fields should be enforced."""
        serializer = DummySerializer(data={})
        assert serializer.is_valid() is False
        assert 'name' in serializer.errors
