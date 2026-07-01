"""apps/operations/licenses/tests/test_models.py — License model unit tests."""

import pytest

from apps.base.constants import UserRole
from apps.operations.licenses.constants import LicenseType
from apps.operations.licenses.models import SoftwareLicense, LicenseAssignment


@pytest.mark.django_db
class TestSoftwareLicenseModel:
    def test_lic_id_auto_generated(self, organization):
        """lic_id is auto-generated with LIC prefix on save."""
        lic = SoftwareLicense.objects.create(
            organization=organization,
            software_name="Microsoft Office",
            license_type=LicenseType.PER_USER.value,
            total_seats=10,
        )
        assert lic.lic_id is not None
        assert lic.lic_id.startswith("LIC")

    def test_lic_id_is_unique(self, organization):
        """Two licenses get different lic_id values."""
        l1 = SoftwareLicense.objects.create(
            organization=organization,
            software_name="Office",
            license_type=LicenseType.PER_USER.value,
            total_seats=10,
        )
        l2 = SoftwareLicense.objects.create(
            organization=organization,
            software_name="Adobe",
            license_type=LicenseType.PER_DEVICE.value,
            total_seats=5,
        )
        assert l1.lic_id != l2.lic_id

    def test_used_seats_zero_when_no_assignments(self, organization):
        """used_seats is 0 when no assignments exist."""
        lic = SoftwareLicense.objects.create(
            organization=organization,
            software_name="Slack",
            license_type=LicenseType.PER_USER.value,
            total_seats=5,
        )
        assert lic.used_seats == 0
        assert lic.available_seats == 5

    def test_used_seats_counts_active_assignments(
        self, organization, employee, asset
    ):
        """used_seats counts only non-revoked assignments."""
        from django.utils import timezone

        lic = SoftwareLicense.objects.create(
            organization=organization,
            software_name="Slack",
            license_type=LicenseType.PER_USER.value,
            total_seats=5,
        )
        LicenseAssignment.objects.create(
            organization=organization, license=lic, employee=employee
        )
        LicenseAssignment.objects.create(
            organization=organization, license=lic, asset=asset
        )
        assert lic.used_seats == 2
        assert lic.available_seats == 3

    def test_used_seats_excludes_revoked(
        self, organization, employee
    ):
        """Revoked assignments are not counted."""
        from django.utils import timezone

        lic = SoftwareLicense.objects.create(
            organization=organization,
            software_name="Slack",
            license_type=LicenseType.PER_USER.value,
            total_seats=5,
        )
        a1 = LicenseAssignment.objects.create(
            organization=organization, license=lic, employee=employee
        )
        a1.revoked_at = timezone.now()
        a1.save(update_fields=["revoked_at"])
        assert lic.used_seats == 0
        assert lic.available_seats == 5

    def test_str_with_name(self, organization):
        """__str__ returns software name and lic_id."""
        lic = SoftwareLicense.objects.create(
            organization=organization,
            software_name="Visual Studio",
            license_type=LicenseType.PER_USER.value,
            total_seats=1,
        )
        s = str(lic)
        assert "Visual Studio" in s

    def test_soft_delete(self, organization):
        """delete() performs soft-delete."""
        lic = SoftwareLicense.objects.create(
            organization=organization,
            software_name="Test",
            license_type=LicenseType.SITE.value,
            total_seats=1,
        )
        lic_id = lic.id
        lic.delete()
        assert not SoftwareLicense.objects.filter(id=lic_id).exists()
        assert SoftwareLicense.objects.all_with_deleted().filter(id=lic_id).exists()


@pytest.mark.django_db
class TestLicenseAssignmentModel:
    def test_is_active_when_not_revoked(self, organization, employee):
        """is_assignment_active is True when revoked_at is None."""
        lic = SoftwareLicense.objects.create(
            organization=organization,
            software_name="Slack",
            license_type=LicenseType.PER_USER.value,
            total_seats=5,
        )
        a = LicenseAssignment.objects.create(
            organization=organization, license=lic, employee=employee
        )
        assert a.is_assignment_active is True

    def test_is_inactive_when_revoked(self, organization, employee):
        """is_assignment_active is False when revoked_at is set."""
        from django.utils import timezone

        lic = SoftwareLicense.objects.create(
            organization=organization,
            software_name="Slack",
            license_type=LicenseType.PER_USER.value,
            total_seats=5,
        )
        a = LicenseAssignment.objects.create(
            organization=organization, license=lic, employee=employee
        )
        a.revoked_at = timezone.now()
        a.save(update_fields=["revoked_at"])
        assert a.is_assignment_active is False

    def test_str_with_employee(self, organization, employee):
        """__str__ shows employee name when assigned to employee."""
        lic = SoftwareLicense.objects.create(
            organization=organization,
            software_name="Slack",
            license_type=LicenseType.PER_USER.value,
            total_seats=5,
        )
        a = LicenseAssignment.objects.create(
            organization=organization, license=lic, employee=employee
        )
        assert employee.user.get_full_name() in str(a)

    def test_str_with_asset(self, organization, asset):
        """__str__ shows asset name when assigned to asset."""
        lic = SoftwareLicense.objects.create(
            organization=organization,
            software_name="Slack",
            license_type=LicenseType.PER_DEVICE.value,
            total_seats=5,
        )
        a = LicenseAssignment.objects.create(
            organization=organization, license=lic, asset=asset
        )
        assert asset.name in str(a)

    def test_related_names(self, organization, employee, asset):
        """Related names are set correctly."""
        lic = SoftwareLicense.objects.create(
            organization=organization,
            software_name="Slack",
            license_type=LicenseType.PER_USER.value,
            total_seats=5,
        )
        assert hasattr(lic, "assignments")
        assert hasattr(employee, "license_assignments")
        assert hasattr(asset, "license_assignments")
