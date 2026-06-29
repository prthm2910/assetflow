"""apps/assets/requests/constants.py — Asset request workflow constants."""

from apps.base.constants import BaseEnum


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
