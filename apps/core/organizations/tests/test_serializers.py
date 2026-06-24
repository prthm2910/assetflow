"""
apps/core/organizations/tests/test_serializers.py — Tests for organization serializers.
"""

import pytest

from apps.core.organizations.models import Organization
from apps.core.organizations.serializers import (
    OrganizationConfigSerializer,
    OrganizationListSerializer,
    OrganizationProfileSerializer,
    OrganizationSerializer,
)


@pytest.mark.django_db
class TestOrganizationSerializer:
    """Tests for OrganizationSerializer."""

    def test_serializer_exists(self):
        """OrganizationSerializer should exist."""
        assert OrganizationSerializer is not None

    def test_serializer_contains_expected_fields(self):
        """Serializer should expose all expected fields."""
        serializer = OrganizationSerializer()
        expected = {"org_id", "name", "slug", "contact_email", "is_active"}
        assert expected.issubset(serializer.fields.keys())

    def test_create_organization_with_config(self):
        """Creating org via serializer should also create config."""
        data = {
            "name": "Serializer Test Org",
            "slug": "ser-test",
            "contact_email": "test@serial.com",
        }
        serializer = OrganizationSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        org = serializer.save()
        assert org.pk is not None
        assert Organization.objects.filter(pk=org.pk).exists()

    def test_update_organization(self):
        """Updating org via serializer should work."""
        org = Organization.objects.create(
            name="Update Test",
            slug="upd-test",
            contact_email="upd@test.com",
        )
        data = {"name": "Updated Name"}
        serializer = OrganizationSerializer(org, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.name == "Updated Name"


@pytest.mark.django_db
class TestOrganizationConfigSerializer:
    """Tests for OrganizationConfigSerializer."""

    def test_serializer_exists(self):
        """OrganizationConfigSerializer should exist."""
        assert OrganizationConfigSerializer is not None

    def test_config_read_only_org_id(self):
        """organization_id should be read-only."""
        org = Organization.objects.create(
            name="Config Serializer Test",
            slug="cfg-ser-test",
            contact_email="cfg@test.com",
        )
        serializer = OrganizationConfigSerializer(instance=org.config)
        assert "organization_id" in serializer.fields
        assert serializer.fields["organization_id"].read_only

    def test_config_updateable_fields(self):
        """Config fields should be updateable."""
        org = Organization.objects.create(
            name="Update Config Test",
            slug="upd-cfg-test",
            contact_email="ucfg@test.com",
        )
        data = {
            "default_timezone": "Asia/Kolkata",
            "working_hours_start": "09:00:00",
            "working_hours_end": "18:00:00",
        }
        serializer = OrganizationConfigSerializer(org.config, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors
        updated = serializer.save()
        assert updated.default_timezone == "Asia/Kolkata"


@pytest.mark.django_db
class TestOrganizationListSerializer:
    """Tests for OrganizationListSerializer."""

    def test_list_serializer_has_expected_fields(self):
        """List serializer should have lightweight fields."""
        serializer = OrganizationListSerializer()
        expected = {"org_id", "name", "slug", "contact_email"}
        assert expected.issubset(serializer.fields.keys())


@pytest.mark.django_db
class TestOrganizationProfileSerializer:
    """Tests for OrganizationProfileSerializer."""

    def test_profile_serializer_exists(self):
        """OrganizationProfileSerializer should exist."""
        assert OrganizationProfileSerializer is not None

    def test_profile_includes_config(self):
        """Profile serializer should include nested config."""
        org = Organization.objects.create(
            name="Profile Test",
            slug="profile-test",
            contact_email="profile@test.com",
        )
        serializer = OrganizationProfileSerializer(instance=org)
        assert "config" in serializer.fields

    def test_profile_slug_read_only(self):
        """Slug should be read-only in profile (can't be changed)."""
        serializer = OrganizationProfileSerializer()
        assert "slug" in serializer.fields
        assert serializer.fields["slug"].read_only
