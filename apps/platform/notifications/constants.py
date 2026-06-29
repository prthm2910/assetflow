"""apps/platform/notifications/constants.py — Notification type constants."""

from apps.base.constants import BaseEnum


class NotificationType(BaseEnum):
    ASSET_ALLOCATED = "asset_allocated"
    REQUEST_APPROVED = "request_approved"
    REQUEST_REJECTED = "request_rejected"
    INCIDENT_UPDATE = "incident_update"
    INCIDENT_ASSIGNED = "incident_assigned"
    LICENSE_EXPIRY = "license_expiry"
    WARRANTY_EXPIRY = "warranty_expiry"
    APPROVAL_NEEDED = "approval_needed"
