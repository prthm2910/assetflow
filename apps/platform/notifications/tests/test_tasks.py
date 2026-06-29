"""apps/platform/notifications/tests/test_tasks.py — Celery task tests."""

from unittest.mock import patch, MagicMock

import pytest
from django.core import mail

from apps.platform.notifications.tasks import send_email_notification


@pytest.mark.django_db
class TestEmailTasks:
    def test_send_email_notification(self):
        """send_email_notification sends an email via Django's mail backend."""
        send_email_notification(
            to="test@example.com",
            subject="Test Subject",
            body="Test Body",
        )
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ["test@example.com"]
        assert mail.outbox[0].subject == "Test Subject"
        assert mail.outbox[0].body == "Test Body"

    def test_send_email_notification_multiple_recipients(self):
        """Can send to multiple recipients (via multiple calls)."""
        send_email_notification(to="a@test.com", subject="Test", body="Body")
        send_email_notification(to="b@test.com", subject="Test", body="Body")
        assert len(mail.outbox) == 2

    def test_send_email_notification_empty_body(self):
        """Handles empty body gracefully."""
        send_email_notification(
            to="test@example.com",
            subject="Test",
            body="",
        )
        assert len(mail.outbox) == 1
        assert mail.outbox[0].body == ""


@pytest.mark.django_db
class TestExpiryTasks:
    def test_check_license_expiry_finds_expiring(self, organization, org_admin_user):
        """check_license_expiry finds licenses expiring in N days."""
        from datetime import timedelta
        from django.utils import timezone

        from apps.operations.licenses.constants import LicenseType
        from apps.operations.licenses.models import SoftwareLicense

        today = timezone.now().date()
        target = today + timedelta(days=30)

        lic = SoftwareLicense.objects.create(
            organization=organization,
            software_name="JetBrains IntelliJ",
            license_type=LicenseType.PER_USER.value,
            total_seats=5,
            expiry_date=target,
        )

        # Ensure org config has admin_user
        org_config = organization.config
        org_config.admin_user = org_admin_user
        org_config.save(update_fields=["admin_user"])

        from apps.platform.notifications.tasks import check_license_expiry
        check_license_expiry()

        from apps.platform.notifications.models import Notification
        assert Notification.objects.filter(
            recipient=org_admin_user,
            notification_type="license_expiry",
        ).count() == 1

    def test_check_license_expiry_no_duplicates(self, organization, org_admin_user):
        """Running twice on same day doesn't create duplicate notifications."""
        from datetime import timedelta
        from django.utils import timezone

        from apps.operations.licenses.constants import LicenseType
        from apps.operations.licenses.models import SoftwareLicense

        today = timezone.now().date()
        target = today + timedelta(days=30)

        SoftwareLicense.objects.create(
            organization=organization,
            software_name="JetBrains",
            license_type=LicenseType.PER_USER.value,
            total_seats=5,
            expiry_date=target,
        )

        org_config = organization.config
        org_config.admin_user = org_admin_user
        org_config.save(update_fields=["admin_user"])

        from apps.platform.notifications.tasks import check_license_expiry

        check_license_expiry()
        check_license_expiry()  # Run again — should not duplicate

        from apps.platform.notifications.models import Notification
        assert Notification.objects.filter(
            recipient=org_admin_user,
            notification_type="license_expiry",
        ).count() == 1

    def test_check_license_expiry_no_admin(self, organization):
        """No notification sent if org has no admin_user."""
        from datetime import timedelta
        from django.utils import timezone

        from apps.operations.licenses.constants import LicenseType
        from apps.operations.licenses.models import SoftwareLicense

        today = timezone.now().date()
        target = today + timedelta(days=30)

        SoftwareLicense.objects.create(
            organization=organization,
            software_name="JetBrains",
            license_type=LicenseType.PER_USER.value,
            total_seats=5,
            expiry_date=target,
        )
        # No admin_user set on org config

        from apps.platform.notifications.tasks import check_license_expiry
        check_license_expiry()

        from apps.platform.notifications.models import Notification
        assert Notification.objects.filter(notification_type="license_expiry").count() == 0

    def test_check_license_expiry_only_active(self, organization, org_admin_user):
        """Deleted licenses are not included in expiry scan."""
        from datetime import timedelta
        from django.utils import timezone

        from apps.operations.licenses.constants import LicenseType
        from apps.operations.licenses.models import SoftwareLicense

        today = timezone.now().date()
        target = today + timedelta(days=30)

        lic = SoftwareLicense.objects.create(
            organization=organization,
            software_name="JetBrains",
            license_type=LicenseType.PER_USER.value,
            total_seats=5,
            expiry_date=target,
        )
        lic.delete()  # soft-delete

        org_config = organization.config
        org_config.admin_user = org_admin_user
        org_config.save(update_fields=["admin_user"])

        from apps.platform.notifications.tasks import check_license_expiry
        check_license_expiry()

        from apps.platform.notifications.models import Notification
        assert Notification.objects.filter(notification_type="license_expiry").count() == 0
