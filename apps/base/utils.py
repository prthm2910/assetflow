"""
apps/base/utils.py — Utility functions for the base module.

HRID (Human-Readable ID) generator using secrets for cryptographic security.
Tenant isolation helper for serializer validation.
"""

import secrets
import string

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _



def generate_unique_id(
    model_class, field_name: str, prefix: str = "", length: int = 6
) -> str:
    """
    Generate a unique alphanumeric HRID (e.g., AST7K3M9).

    Uses secrets.choice() for cryptographic randomness. Relies on a DB unique
    constraint — retries on collision instead of pre-checking to avoid race
    conditions.

    Args:
        model_class: The Django model class to check against.
        field_name: The field name to check for uniqueness (e.g., 'asset_id').
        prefix: Optional prefix for the ID (e.g., 'AST').
        length: Number of random alphanumeric characters (default 6).

    Returns:
        A unique ID string.
    """
    alphabet = string.ascii_uppercase + string.digits
    while True:
        random_suffix = "".join(secrets.choice(alphabet) for _ in range(length))
        new_id = f"{prefix}{random_suffix}"
        manager = getattr(model_class, "all_objects", model_class.objects)
        try:
            manager.get(**{field_name: new_id})
        except model_class.DoesNotExist:
            return new_id  # Unique, safe to use


def validate_tenant_isolation(user, field_name: str, obj, entity_label: str = "") -> None:
    """
    Validate that a related object belongs to the same organization as the user.

    No-op for super admins. Raises ValidationError if the object's organization
    doesn't match the user's organization.

    Args:
        user: The requesting user.
        field_name: The serializer field name (used in error key).
        obj: The related model instance being validated.
        entity_label: Human-readable label for error message (e.g. "asset", "category").
            Defaults to field_name if not provided.

    Raises:
        serializers.ValidationError: If org mismatch detected.
    """

    # Skip for super admins
    if getattr(user, "is_super_admin", False):
        return

    user_org = getattr(user, "organization", None)
    if not user_org or not obj:
        return

    label = entity_label or field_name
    if getattr(obj, "organization_id", None) != user_org.id:
        raise serializers.ValidationError(
            {field_name: f"This {label} does not belong to your organization."}
        )


def validate_tenant_isolation_multi(user, checks: list[tuple[str, object, str]]) -> None:
    """
    Batch tenant validation for multiple related objects in one serializer.

    Args:
        user: The requesting user.
        checks: List of (field_name, obj, entity_label) tuples.

    Raises:
        serializers.ValidationError: On first org mismatch.
    """
    for field_name, obj, label in checks:
        validate_tenant_isolation(user, field_name, obj, label)
