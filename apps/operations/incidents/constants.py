"""apps/operations/incidents/constants.py — Incident workflow constants."""

from apps.base.constants import BaseEnum


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
