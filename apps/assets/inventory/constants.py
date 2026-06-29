"""apps/assets/inventory/constants.py — Asset lifecycle statuses."""

from apps.base.constants import BaseEnum


class AssetStatus(BaseEnum):
    PROCURED = "procured"
    AVAILABLE = "available"
    ALLOCATED = "allocated"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"
