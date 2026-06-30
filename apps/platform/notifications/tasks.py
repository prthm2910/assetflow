"""apps/platform/notifications/tasks.py — Celery tasks for notifications."""

from datetime import timedelta
from typing import Callable

from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.db.models import QuerySet
from django.utils import timezone

from apps.platform.notifications.constants import NotificationType
from apps.platform.notifications.models import NotificationAudit
from apps.platform.notifications.services import InAppChannel, NotificationService

# Retry defaults — prevent silent notification loss on transient failures
MAX_RETRIES = 3
EMAIL_RETRY_DELAY = 60    # 1 minute
SCAN_RETRY_DELAY = 300    # 5 minutes (external DB queries)


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


def _check_expiry(
    model,
    date_field: str,
    notification_type: NotificationType,
    name_fn: Callable,
    entity_singular: str,
    entity_plural: str,
):
    """
    Scan for objects expiring at each threshold (30, 14, 7, 1, 0 days).

    Aggregates notifications per org to prevent alert fatigue.

    Args:
        model: The Django model class (e.g. SoftwareLicense, Asset).
        date_field: The date field to check (e.g. "expiry_date", "warranty_expiry").
        notification_type: The NotificationType enum member.
        name_fn: Callable that extracts the display name from an instance.
        entity_singular: Singular noun for messages ("license").
        entity_plural: Plural noun for messages ("licenses").
    """
    today = timezone.now().date()
    thresholds = [30, 14, 7, 1, 0]
    content_type = ContentType.objects.get_for_model(model)
    notif_type_value = notification_type.value

    for days in thresholds:
        target = today + timedelta(days=days)
        expiring: QuerySet = model.objects.filter(
            **{f"{date_field}": target, "is_deleted": False},
        ).select_related("organization__config__admin_user")

        # Bulk fetch already notified IDs for this threshold today
        notified_ids = set(
            NotificationAudit.objects.filter(
                content_type=content_type,
                threshold_days=days,
                notification_type=notif_type_value,
                sent_at__date=today,
            ).values_list("object_id", flat=True)
        )

        # Group by organization, skip already-notified
        by_org = {}
        for obj in expiring:
            if str(obj.pk) in notified_ids:
                continue
            org = obj.organization
            if org not in by_org:
                by_org[org] = []
            by_org[org].append(obj)

        # Send one aggregated notification per org
        for org, items in by_org.items():
            admin_user = org.config.admin_user if hasattr(org, "config") and org.config.admin_user else None
            if not admin_user:
                continue

            names = ", ".join(name_fn(item) for item in items[:5])
            if len(items) > 5:
                names += f" and {len(items) - 5} more"

            if days == 0:
                title = f"{len(items)} {entity_plural} expiring TODAY"
                msg = f"The following {entity_plural} expire today: {names}"
            else:
                title = f"{len(items)} {entity_plural} expiring in {days} day(s)"
                msg = f"The following {entity_plural} expire in {days} days: {names}"

            NotificationService.send(
                recipient=admin_user,
                notification_type=notif_type_value,
                title=title,
                message=msg,
                channels=[InAppChannel()],
                organization=org,
            )

            for item in items:
                _record_notification(item, days, notif_type_value, org)


@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    default_retry_delay=SCAN_RETRY_DELAY,
)
def check_license_expiry(self):
    """
    Scan for software licenses expiring at each threshold (30, 14, 7, 1, 0 days).

    Runs daily at midnight via Celery Beat.
    Retries up to 3 times on transient failures (DB/Redis down).
    """
    from apps.operations.licenses.models import SoftwareLicense

    try:
        _check_expiry(
            model=SoftwareLicense,
            date_field="expiry_date",
            notification_type=NotificationType.LICENSE_EXPIRY,
            name_fn=lambda lic: lic.software_name,
            entity_singular="license",
            entity_plural="licenses",
        )
    except Exception as exc:
        self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    default_retry_delay=SCAN_RETRY_DELAY,
)
def check_warranty_expiry(self):
    """
    Scan for assets with warranty expiring at each threshold (30, 14, 7, 1, 0 days).

    Runs daily at midnight via Celery Beat.
    Retries up to 3 times on transient failures (DB/Redis down).
    """
    from apps.assets.inventory.models import Asset

    try:
        _check_expiry(
            model=Asset,
            date_field="warranty_expiry",
            notification_type=NotificationType.WARRANTY_EXPIRY,
            name_fn=lambda a: a.name,
            entity_singular="asset warranty",
            entity_plural="assets' warranty",
        )
    except Exception as exc:
        self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    default_retry_delay=EMAIL_RETRY_DELAY,
)
def send_email_notification(self, to, subject, body):
    """
    Send an email notification asynchronously via Celery.

    Retries up to 3 times with 60-second delays on SMTP failure.

    Usage:
        send_email_notification.delay(
            to="user@example.com",
            subject="License expiring",
            body="Your JetBrains license expires in 7 days",
        )
    """
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=None,  # Uses DEFAULT_FROM_EMAIL
            recipient_list=[to],
            fail_silently=False,
        )
    except Exception as exc:
        self.retry(exc=exc)
