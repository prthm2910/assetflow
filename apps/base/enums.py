"""
apps/base/enums.py — System-wide enumeration types.

All enums inherit from BaseEnum which provides a .choices() classmethod
that returns Django-compatible (value, label) tuples for use in model field
choices and serializer choices.
"""

from enum import Enum


class BaseEnum(Enum):
    """
    Base Enum for all system-wide choices. Auto-generates Django (value, label) tuples.

    Usage:
        class UserRole(BaseEnum):
            ADMIN = 'admin'
            EMPLOYEE = 'employee'

        # Returns [('admin', 'Admin'), ('employee', 'Employee')]
        UserRole.choices()
    """

    @classmethod
    def choices(cls):
        """Return Django-compatible (value, label) tuples for all members."""
        return [
            (member.value, member.value.replace("_", " ").title())
            for member in cls
            if not member.name.startswith("_")
        ]

    @classmethod
    def values(cls):
        """Return a list of all member values."""
        return [member.value for member in cls if not member.name.startswith("_")]


# ==============================================================================
# User Roles
# ==============================================================================
class UserRole(BaseEnum):
    SUPER_ADMIN = "super_admin"
    ORG_ADMIN = "org_admin"
    EMPLOYEE = "employee"


# ==============================================================================
# Asset Lifecycle
# ==============================================================================
class AssetStatus(BaseEnum):
    PROCURED = "procured"
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"


# ==============================================================================
# Request Workflow
# ==============================================================================
class RequestStatus(BaseEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class RequestPriority(BaseEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ==============================================================================
# Incident Workflow
# ==============================================================================
class IncidentStatus(BaseEnum):
    REPORTED = "reported"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentCategory(BaseEnum):
    HARDWARE = "hardware"
    SOFTWARE = "software"
    PHYSICAL_DAMAGE = "physical_damage"
    PERFORMANCE = "performance"
    OTHER = "other"


# ==============================================================================
# License Types
# ==============================================================================
class LicenseType(BaseEnum):
    PER_USER = "per_user"
    PER_DEVICE = "per_device"
    SITE = "site"


# ==============================================================================
# Audit Actions
# ==============================================================================
class AuditAction(BaseEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ALLOCATE = "allocate"
    APPROVE = "approve"
    REJECT = "reject"


# ==============================================================================
# Notification Types
# ==============================================================================
class NotificationType(BaseEnum):
    ASSET_ALLOCATED = "asset_allocated"
    REQUEST_APPROVED = "request_approved"
    REQUEST_REJECTED = "request_rejected"
    INCIDENT_UPDATE = "incident_update"
    LICENSE_EXPIRY = "license_expiry"
    WARRANTY_EXPIRY = "warranty_expiry"
    INCIDENT_ASSIGNED = "incident_assigned"
    APPROVAL_NEEDED = "approval_needed"
