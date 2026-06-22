"""
apps/base/signals.py — Django signals for audit logging.

These signals capture create/update/delete actions on tracked models and log them
to the AuditLog model (when Module 12 is implemented).

audit_post_save: Logs CREATE and UPDATE actions with old/new data diff.
audit_pre_delete: Logs DELETE action.

Signals are registered in apps/base/apps.py -> ready().
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver


def _get_audit_log_model():
    """
    Lazily import AuditLog to avoid circular imports.
    AuditLog is defined in apps/platform/audit/models.py (Module 12).
    """
    try:
        from apps.platform.audit.models import AuditLog
        return AuditLog
    except ImportError:
        return None


def _get_request_context():
    """Get user and IP from thread-local request context."""
    try:
        from apps.base.middleware import get_current_user, get_current_ip
        return get_current_user(), get_current_ip()
    except ImportError:
        return None, None


def _serialize_instance(instance, fields=None):
    """
    Serialize a model instance to a dict for audit logging.
    Excludes sensitive fields and relations.
    """
    if instance is None:
        return None

    exclude = {'password', 'token', 'secret', '_state', 'all_objects', 'objects'}
    if fields:
        exclude.update(fields)

    data = {}
    for field in instance._meta.fields:
        fname = field.name
        if fname in exclude:
            continue
        try:
            value = getattr(instance, fname, None)
            if hasattr(value, 'pk'):
                # Foreign key — store the ID
                data[fname] = str(value.pk) if value else None
            elif hasattr(value, 'all'):
                # Related manager — skip
                continue
            else:
                data[fname] = str(value) if value is not None else None
        except Exception:
            data[fname] = None
    return data


def _get_old_data(instance):
    """
    Get the old data from database before save (for UPDATE detection).
    Only works for existing instances.
    """
    if instance.pk is None:
        return None  # CREATE — no old data

    try:
        old_instance = instance.__class__.all_objects.get(pk=instance.pk)
        return _serialize_instance(old_instance)
    except instance.__class__.DoesNotExist:
        return None


@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    """
    Log CREATE and UPDATE actions to AuditLog.

    Logs CREATE with new_data only.
    Logs UPDATE with old_data and new_data.
    """
    AuditLog = _get_audit_log_model()
    if AuditLog is None:
        return

    # Skip if sender is AuditLog itself (avoid infinite loop)
    if sender.__name__ == 'AuditLog':
        return

    # Skip abstract models
    if getattr(sender._meta, 'abstract', False):
        return

    user, ip = _get_request_context()
    action = 'create' if created else 'update'
    new_data = _serialize_instance(instance)
    old_data = None if created else _get_old_data(instance)

    # Build kwargs for AuditLog
    kwargs_create = {
        'action': action,
        'model_name': sender.__name__,
        'object_id': str(instance.pk),
        'new_data': new_data,
    }

    # Add org from instance if available
    if hasattr(instance, 'organization'):
        kwargs_create['organization'] = instance.organization

    # Add user if available
    if user:
        kwargs_create['user'] = user
    if ip:
        kwargs_create['ip_address'] = ip

    # Only add old_data for updates
    if not created:
        kwargs_create['old_data'] = old_data

    try:
        AuditLog.objects.create(**kwargs_create)
    except Exception:
        # Don't let audit logging failures break the main operation
        pass


@receiver(pre_delete)
def audit_pre_delete(sender, instance, **kwargs):
    """
    Log DELETE action to AuditLog (before the actual delete).
    """
    AuditLog = _get_audit_log_model()
    if AuditLog is None:
        return

    # Skip if sender is AuditLog itself
    if sender.__name__ == 'AuditLog':
        return

    # Skip abstract models
    if getattr(sender._meta, 'abstract', False):
        return

    user, ip = _get_request_context()
    old_data = _serialize_instance(instance)

    kwargs_create = {
        'action': 'delete',
        'model_name': sender.__name__,
        'object_id': str(instance.pk),
        'old_data': old_data,
    }

    # Add org from instance if available
    if hasattr(instance, 'organization'):
        kwargs_create['organization'] = instance.organization

    # Add user if available
    if user:
        kwargs_create['user'] = user
    if ip:
        kwargs_create['ip_address'] = ip

    try:
        AuditLog.objects.create(**kwargs_create)
    except Exception:
        # Don't let audit logging failures break the main operation
        pass
