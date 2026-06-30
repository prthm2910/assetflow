"""apps/base/fields.py — Reusable DRF field classes."""

from rest_framework import serializers


class EmployeeNameField(serializers.SerializerMethodField):
    """
    SerializerMethodField that resolves an Employee's user full_name.

    Handles the null-safe chain: obj.<source> → obj.<source>.user → get_full_name()

    Usage:
        reported_by_name = EmployeeNameField(source="reported_by")
        assigned_to_name = EmployeeNameField(source="assigned_to")
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)

    def to_representation(self, value):
        """
        value is the Employee instance (from the source).
        Returns the user's full_name or None.
        """
        if value is None:
            return None
        user = getattr(value, "user", None)
        if user is None:
            return None
        return user.get_full_name()
