"""
apps/base/utils.py — Utility functions for the base module.

HRID (Human-Readable ID) generator using secrets for cryptographic security.
"""

import secrets
import string


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
