"""
apps/core/users/models.py — Custom User model and Password Reset Token.

Uses AbstractUser for built-in auth functionality and adds HRID via save() override.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField

from apps.base.enums import UserRole
from apps.base.utils import generate_unique_id


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.

    Inherited fields from AbstractUser:
    - id (AutoField): Primary key
    - username (str): Unique identifier for authentication
    - first_name (str): User's first name
    - last_name (str): User's last name
    - email (str): Required email address
    - password (str): Hashed password
    - is_staff (bool): Can access admin site
    - is_active (bool): Account is active
    - is_superuser (bool): Has all permissions
    - last_login (datetime): Last login timestamp
    - date_joined (datetime): Account creation timestamp

    Added fields:
    - user_id: HRID (USRXXXXXX) for public API exposure
    - role: Role-based access control
    - organization_id: Multi-tenancy support
    - must_change_password: Security flag for first login

    Note: organization_id is nullable until Organization model (Module 3) is ready.
    """

    # HRID field for public API exposure
    user_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        help_text="Format: USRXXXXXX",
    )
    _display_id_prefix = "USR"
    _display_id_field = "user_id"

    # Organization membership — nullable until Organization model is ready
    organization_id = models.UUIDField(null=True, blank=True, db_index=True)

    # Role-based access control
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices(),
        default=UserRole.EMPLOYEE.value,
        db_index=True,
    )

    # Security — forces password change on first login
    must_change_password = models.BooleanField(default=True)

    # Phone number (e.g., +12125551234)
    phone = PhoneNumberField(null=True, blank=True, region=None) # type: ignore

    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"

    def save(self, *args, **kwargs):
        """Auto-generate HRID on first save."""
        if not self.user_id:
            self.user_id = generate_unique_id(User, "user_id", "USR")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email


class PasswordResetToken(models.Model):
    """
    Token for password reset flow.

    Usage:
    1. User requests reset → create token with 24hr expiry
    2. Email sent with reset link containing token
    3. User submits new password with token → validate and use
    4. Token marked as used after successful reset
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.CharField(max_length=128, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "password_reset_tokens"
        verbose_name = "password reset token"
        verbose_name_plural = "password reset tokens"

    def __str__(self):
        return f"Token for {self.user.email}"

    @property
    def is_valid(self):
        """Check if token is valid (not used and not expired)."""
        return not self.used and self.expires_at > timezone.now()
