"""apps/operations/licenses/constants.py — License type constants."""

from apps.base.constants import BaseEnum


class LicenseType(BaseEnum):
    PER_USER = "per_user"
    PER_DEVICE = "per_device"
    SITE = "site"
