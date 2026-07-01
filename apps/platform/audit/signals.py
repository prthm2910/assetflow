"""
apps/platform/audit/signals.py — Django signals for audit logging.

Registered on all pre_save, post_save, and pre_delete events.
Captures create/update/delete actions and writes AuditLog entries.

Signals are registered in apps/platform/audit/apps.py -> ready().
"""

from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
import logging

from apps.platform.audit.models import AuditLog
from apps.platform.audit.constants import AuditAction
from apps.base.middleware import (
    get_current_user,
    get_current_ip,
    get_current_request_id,
    get_current_request,
)

audit_logger = logging.getLogger(__name__)


def _serialize_instance(instance, fields=None):
    """
    Serialize a model instance to a dict for audit logging.
    Excludes sensitive fields and relations.
    """
    if instance is None:
        return None

    exclude = {"password", "token", "secret", "_state", "all_objects", "objects"}
    if fields:
        exclude.update(fields)

    data = {}
    for field in instance._meta.fields:
        fname = field.name
        if fname in exclude:
            continue
        try:
            value = getattr(instance, fname, None)
            if hasattr(value, "pk"):
                # Foreign key — store the ID
                data[fname] = str(value.pk) if value else None
            elif hasattr(value, "all"):
                # Related manager — skip
                continue
            else:
                data[fname] = str(value) if value is not None else None
        except Exception:
            data[fname] = None
    return data


def _get_old_data(instance):
    """Get the old data captured during pre_save."""
    return getattr(instance, "_old_data", None)


def _build_audit_kwargs(instance, action, old_data=None, new_data=None):
    """Build shared kwargs for AuditLog creation."""
    kwargs = {
        "action": action,
        "model_name": instance.__class__.__name__,
        "object_id": instance.pk,
    }
    if hasattr(instance, "organization"):
        kwargs["organization"] = instance.organization

    user = get_current_user()
    if user:
        kwargs["user"] = user

    ip = get_current_ip()
    if ip:
        kwargs["ip_address"] = ip

    request_id = get_current_request_id()
    if request_id:
        kwargs["request_id"] = request_id

    request = get_current_request()
    if request:
        kwargs["path"] = request.path

    # Build changes dict: {"old": {...}, "new": {...}}
    changes = {}
    if old_data is not None:
        changes["old"] = old_data
    if new_data is not None:
        changes["new"] = new_data
    if changes:
        kwargs["changes"] = changes

    return kwargs


@receiver(pre_save)
def audit_pre_save(sender, instance, **kwargs):
    """
    Capture the old state of the instance before it is saved.
    Stored on instance._old_data for retrieval in post_save.
    """
    if getattr(sender._meta, "abstract", False) or sender.__name__ == "AuditLog":
        return
    app_label = sender._meta.app_label
    if app_label in ("contenttypes", "sessions", "auth", "admin") or app_label.startswith("django"):
        return
    if not hasattr(instance, "organization"):
        return
    if instance.pk:
        manager = getattr(sender, "all_objects", None)
        if manager is None:
            instance._old_data = None
            return
        try:
            old_instance = manager.get(pk=instance.pk)
            instance._old_data = _serialize_instance(old_instance)
        except sender.DoesNotExist:
            instance._old_data = None


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    """
    Log CREATE and UPDATE actions to AuditLog.

    Logs CREATE with new_data only.
    Logs UPDATE with old_data and new_data.
    """
    # Skip if sender is AuditLog itself (avoid infinite loop)
    if sender.__name__ == "AuditLog":
        return

    # Skip abstract models
    if getattr(sender._meta, "abstract", False):
        return

    # Skip Django's built-in models (migrations, contenttypes, sessions, etc.)
    app_label = sender._meta.app_label
    if app_label in ("contenttypes", "sessions", "auth", "admin"):
        return
    if app_label.startswith("django"):
        return

    # Skip if model has no organization (can't scope the audit entry)
    if not hasattr(instance, "organization"):
        return

    action = AuditAction.CREATE.value if created else AuditAction.UPDATE.value
    new_data = _serialize_instance(instance)
    old_data = None if created else _get_old_data(instance)

    # Skip logging if nothing actually changed (e.g. auto-saves, background tasks)
    if not created and old_data == new_data:
        return

    kwargs_create = _build_audit_kwargs(
        instance, action,
        old_data=old_data, new_data=new_data,
    )

    try:
        AuditLog.objects.create(**kwargs_create)
        audit_logger.debug(
            "Audit log created: %s %s (pk=%s)",
            action,
            instance.__class__.__name__,
            instance.pk,
        )
    except Exception:
        audit_logger.exception(
            "Audit log failed for %s on %s", action, sender.__name__
        )


@receiver(pre_delete)
def audit_pre_delete(sender, instance, **kwargs):
    """
    Log DELETE action to AuditLog (before the actual delete).
    """
    # Skip if sender is AuditLog itself
    if sender.__name__ == "AuditLog":
        return

    # Skip abstract models
    if getattr(sender._meta, "abstract", False):
        return

    # Skip Django's built-in models
    app_label = sender._meta.app_label
    if app_label in ("contenttypes", "sessions", "auth", "admin"):
        return
    if app_label.startswith("django"):
        return

    # Skip if model has no organization
    if not hasattr(instance, "organization"):
        return

    old_data = _serialize_instance(instance)

    kwargs_create = _build_audit_kwargs(
        instance, AuditAction.DELETE.value,
        old_data=old_data,
    )

    try:
        AuditLog.objects.create(**kwargs_create)
        audit_logger.debug(
            "Audit log created: delete %s (pk=%s)",
            instance.__class__.__name__,
            instance.pk,
        )
    except Exception:
        audit_logger.exception(
            "Audit log failed for delete on %s", sender.__name__
        )
