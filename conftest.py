"""
conftest.py — Project-level pytest fixtures for DRF API testing.

Provides reusable authenticated and unauthenticated API clients
that all child apps import via pytest's fixture system.
"""
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


# ---------------------------------------------------------------------------
# Unauthenticated client
# ---------------------------------------------------------------------------

@pytest.fixture
def api_client():
    """Unauthenticated API client — simulates anonymous requests."""
    return APIClient()


# ---------------------------------------------------------------------------
# User fixtures (model objects, no auth attached)
# ---------------------------------------------------------------------------

@pytest.fixture
def user(db):
    """Regular employee user"""
    return User.objects.create_user(
        username='employee',
        email='employee@test.com',
        password='testpass123',
        first_name='Test',
        last_name='Employee',
    )


@pytest.fixture
def org_admin_user(db):
    """Organization-level admin user — placeholder until Module 2."""
    return User.objects.create_user(
        username='org_admin',
        email='org_admin@test.com',
        password='testpass123',
        first_name='Org',
        last_name='Admin',
    )


@pytest.fixture
def super_admin_user(db):
    """Super admin user — placeholder until Module 2."""
    return User.objects.create_user(
        username='super_admin',
        email='super_admin@test.com',
        password='testpass123',
        first_name='Super',
        last_name='Admin',
        is_staff=True,
        is_superuser=True,
    )


# ---------------------------------------------------------------------------
# Authenticated client fixtures — APIClient pre-authenticated per role
# ---------------------------------------------------------------------------

@pytest.fixture
def employee_client(api_client, user):
    """APIClient authenticated as a regular employee."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def org_admin_client(api_client, org_admin_user):
    """APIClient authenticated as an org admin."""
    api_client.force_authenticate(user=org_admin_user)
    return api_client


@pytest.fixture
def super_admin_client(api_client, super_admin_user):
    """APIClient authenticated as a super admin."""
    api_client.force_authenticate(user=super_admin_user)
    return api_client


# ---------------------------------------------------------------------------
# Aliases for common naming conventions used across child app tests
# ---------------------------------------------------------------------------

authenticated_client = employee_client  #: Authenticated as employee
admin_client = super_admin_client      #: Admin-level access
