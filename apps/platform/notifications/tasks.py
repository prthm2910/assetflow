"""apps/platform/notifications/tasks.py — Celery tasks for notifications."""

from datetime import timedelta

from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.utils import timezone

from apps.operations.licenses.models import SoftwareLicense
from apps.platform.notifications.constants import NotificationType
from apps.platform.notifications.models import Notification, NotificationAudit
from apps.platform.notifications.services import InAppChannel, NotificationService


def _record_notification(content_object, threshold_days, notification_type, organization):
    """Record that a notification was sent (prevents duplicates)."""
    content_type = ContentType.objects.get_for_model(content_object)
    NotificationAudit.objects.create(
        organization=organization,
        content_type=content_type,
        object_id=str(content_object.pk),
        threshold_days=threshold_days,
        notification_type=notification_type,
    )


@shared_task
def check_license_expiry():
    """
    Scan for licenses expiring at each threshold (30, 14, 7, 1, 0 days).

    Runs daily at midnight via Celery Beat.
    Aggregates notifications per org to prevent alert fatigue.
    """
    today = timezone.now().date()
    thresholds = [30, 14, 7, 1, 0]
    content_type = ContentType.objects.get_for_model(SoftwareLicense)

    for days in thresholds:
        target = today + timedelta(days=days)
        expiring = SoftwareLicense.objects.filter(
            expiry_date=target,
            is_deleted=False,
        ).select_related("organization__config__admin_user")

        # Bulk fetch already notified license IDs for this threshold today
        notified_ids = set(
            NotificationAudit.objects.filter(
                content_type=content_type,
                threshold_days=days,
                notification_type=NotificationType.LICENSE_EXPIRY.value,
                sent_at__date=today,
            ).values_list("object_id", flat=True)
        )

        # Group by organization
        by_org = {}
        for lic in expiring:
            if str(lic.pk) in notified_ids:
                continue

            org = lic.organization
            if org not in by_org:
                by_org[org] = []
            by_org[org].append(lic)

        # Send one aggregated notification per org
        for org, licenses in by_org.items():
            admin_user = org.config.admin_user if hasattr(org, "config") and org.config.admin_user else None
            if not admin_user:
                continue

            names = ", ".join(lic.software_name for lic in licenses[:5])
            if len(licenses) > 5:
                names += f" and {len(licenses) - 5} more"

            if days == 0:
                title = f"{len(licenses)} license(s) expiring TODAY"
                msg = f"The following licenses expire today: {names}"
            else:
                title = f"{len(licenses)} license(s) expiring in {days} day(s)"
                msg = f"The following licenses expire in {days} days: {names}"

            NotificationService.send(
                recipient=admin_user,
                notification_type=NotificationType.LICENSE_EXPIRY.value,
                title=title,
                message=msg,
                channels=[InAppChannel()],
                organization=org,
            )

            for lic in licenses:
                _record_notification(lic, days, NotificationType.LICENSE_EXPIRY.value, org)


@shared_task
def check_warranty_expiry():
    """
    Scan for assets with warranty expiring at each threshold (30, 14, 7, 1, 0 days).

    Runs daily at midnight via Celery Beat.
    """
    today = timezone.now().date()
    thresholds = [30, 14, 7, 1, 0]
    from apps.assets.inventory.models import Asset

    content_type = ContentType.objects.get_for_model(Asset)

    for days in thresholds:
        target = today + timedelta(days=days)

        expiring = Asset.objects.filter(
            warranty_expiry=target,
            is_deleted=False,
        ).select_related("organization__config__admin_user")

        # Bulk fetch already notified asset IDs for this threshold today
        notified_ids = set(
            NotificationAudit.objects.filter(
                content_type=content_type,
                threshold_days=days,
                notification_type=NotificationType.WARRANTY_EXPIRY.value,
                sent_at__date=today,
            ).values_list("object_id", flat=True)
        )

        # Group by organization
        by_org = {}
        for asset in expiring:
            if str(asset.pk) in notified_ids:
                continue

            org = asset.organization
            if org not in by_org:
                by_org[org] = []
            by_org[org].append(asset)

        # Send one aggregated notification per org
        for org, assets in by_org.items():
            admin_user = org.config.admin_user if hasattr(org, "config") and org.config.admin_user else None
            if not admin_user:
                continue

            names = ", ".join(a.name for a in assets[:5])
            if len(assets) > 5:
                names += f" and {len(assets) - 5} more"

            if days == 0:
                title = f"{len(assets)} asset(s) warranty expiring TODAY"
                msg = f"The following assets' warranty expires today: {names}"
            else:
                title = f"{len(assets)} asset(s) warranty expiring in {days} day(s)"
                msg = f"The following assets' warranty expires in {days} days: {names}"

            NotificationService.send(
                recipient=admin_user,
                notification_type=NotificationType.WARRANTY_EXPIRY.value,
                title=title,
                message=msg,
                channels=[InAppChannel()],
                organization=org,
            )

            for asset in assets:
                _record_notification(asset, days, NotificationType.WARRANTY_EXPIRY.value, org)


@shared_task
def send_email_notification(to, subject, body):
    """
    Send an email notification asynchronously via Celery.

    Usage:
        send_email_notification.delay(
            to="user@example.com",
            subject="License expiring",
            body="Your JetBrains license expires in 7 days",
        )
    """
    send_mail(
        subject=subject,
        message=body,
        from_email=None,  # Uses DEFAULT_FROM_EMAIL
        recipient_list=[to],
        fail_silently=False,
    )
