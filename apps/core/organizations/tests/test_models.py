"""
apps/core/organizations/tests/test_models.py — Tests for Organization and OrganizationConfig models.
"""

import pytest

from apps.core.organizations.models import Organization, OrganizationConfig


@pytest.mark.django_db
class TestOrganizationModel:
    """Tests for Organization model."""

    def test_create_organization_generates_org_id(self):
        """Creating an organization should auto-generate an org_id."""
        org = Organization.objects.create(
            name="Test Corp",
            slug="test-corp",
            contact_email="admin@testcorp.com",
        )
        assert org.org_id is not None
        assert org.org_id.startswith("ORG")
        assert len(org.org_id) == 9  # ORG + 6 chars

    def test_org_id_is_unique(self):
        """org_id should be unique across all organizations."""
        org1 = Organization.objects.create(
            name="Acme",
            slug="acme",
            contact_email="acme@acme.com",
        )
        org2 = Organization.objects.create(
            name="Acme Two",
            slug="acme-two",
            contact_email="acme2@acme.com",
        )
        assert org1.org_id != org2.org_id

    def test_org_str_representation(self):
        """String representation should include name and org_id."""
        org = Organization.objects.create(
            name="Widget Inc",
            slug="widget-inc",
            contact_email="admin@widget.com",
        )
        assert "Widget Inc" in str(org)
        assert org.org_id in str(org)

    def test_organization_default_active(self):
        """New organizations should be active by default."""
        org = Organization.objects.create(
            name="Active Test",
            slug="active-test",
            contact_email="test@test.com",
        )
        assert org.is_active is True

    def test_organization_soft_delete(self):
        """Deleting an organization should soft-delete."""
        org = Organization.objects.create(
            name="To Delete",
            slug="to-delete",
            contact_email="delete@test.com",
        )
        org.delete()
        # Should not appear in default queryset
        assert Organization.objects.filter(id=org.id).count() == 0
        # Should still exist in database
        assert Organization.objects.all_with_deleted().filter(id=org.id).count() == 1

    def test_organization_restore(self):
        """Restoring a soft-deleted organization should work."""
        org = Organization.objects.create(
            name="To Restore",
            slug="to-restore",
            contact_email="restore@test.com",
        )
        org.delete()
        org.restore()
        assert Organization.objects.filter(id=org.id).exists()
        assert org.is_active is True

    def test_organization_has_config_after_create(self):
        """Creating an org should auto-create a config."""
        org = Organization.objects.create(
            name="With Config",
            slug="with-config",
            contact_email="config@test.com",
        )
        assert hasattr(org, "config")
        assert isinstance(org.config, OrganizationConfig)

    def test_get_admin_user_returns_admin(self):
        """get_admin_user should return the admin user from config."""
        org = Organization.objects.create(
            name="Admin Test",
            slug="admin-test",
            contact_email="admin@test.com",
        )
        # No admin set yet
        assert org.get_admin_user() is None


@pytest.mark.django_db
class TestOrganizationConfigModel:
    """Tests for OrganizationConfig model."""

    def test_config_auto_creates_with_organization(self):
        """OrganizationConfig should be created when an Organization is saved."""
        org = Organization.objects.create(
            name="Config Test",
            slug="config-test",
            contact_email="ctest@test.com",
        )
        assert OrganizationConfig.objects.filter(organization=org).exists()

    def test_config_default_timezone(self):
        """Config should have a default timezone."""
        org = Organization.objects.create(
            name="TZ Test",
            slug="tz-test",
            contact_email="tz@test.com",
        )
        assert org.config.default_timezone == "UTC"

    def test_config_default_working_days(self):
        """Config working_days should default to Mon–Fri."""
        org = Organization.objects.create(
            name="Workdays Test",
            slug="workdays-test",
            contact_email="wd@test.com",
        )
        assert org.config.working_days == [0, 1, 2, 3, 4]

    def test_config_request_approval_default(self):
        """request_approval_required should default to True."""
        org = Organization.objects.create(
            name="Approval Test",
            slug="approval-test",
            contact_email="ap@test.com",
        )
        assert org.config.request_approval_required is True

    def test_config_notification_flags_default_true(self):
        """Notification flags should default to True."""
        org = Organization.objects.create(
            name="Notify Test",
            slug="notify-test",
            contact_email="nf@test.com",
        )
        assert org.config.notify_on_asset_allocated is True
        assert org.config.notify_on_request_submitted is True
        assert org.config.notify_on_incident_reported is True

    def test_config_str_representation(self):
        """String representation should include organization name."""
        org = Organization.objects.create(
            name="Str Test",
            slug="str-test",
            contact_email="str@test.com",
        )
        assert str(org.config) == f"Config for {org.name}"
