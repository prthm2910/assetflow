"""apps/platform/audit/constants.py — Audit action types."""

from apps.base.constants import BaseEnum


class AuditAction(BaseEnum):
    """Actions tracked in AuditLog."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    ALLOCATE = "allocate"
    APPROVE = "approve"
    REJECT = "reject"
