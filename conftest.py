"""
conftest.py — Project-level pytest fixtures for DRF API testing.

Provides reusable authenticated and unauthenticated API clients
that all child apps import via pytest's fixture system.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


User = get_user_model()


# ---------------------------------------------------------------------------
# Organization fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def organization(transactional_db):
    """Create a test organization with config."""
    from apps.core.organizations.models import Organization

    return Organization.objects.create(
        name="Test Organization",
        slug="test-org",
        contact_email="admin@testorg.com",
        contact_phone="+1234567890",
        address="123 Test St",
        city="Testville",
        country="Testland",
    )


# ---------------------------------------------------------------------------
# User fixtures (model objects, no auth attached)
# ---------------------------------------------------------------------------


@pytest.fixture
def user(transactional_db, organization):
    """Regular employee user assigned to an organization."""
    return User.objects.create_user(
        username="employee",
        email="employee@test.com",
        password="testpass123",
        first_name="Test",
        last_name="Employee",
        role="employee",
        organization_id=organization.id,
    )


@pytest.fixture
def org_admin_user(transactional_db, organization):
    """Organization-level admin user assigned to an organization."""
    from apps.base.enums import UserRole

    return User.objects.create_user(
        username="org_admin",
        email="org_admin@test.com",
        password="testpass123",
        first_name="Org",
        last_name="Admin",
        role=UserRole.ORG_ADMIN.value,
        organization_id=organization.id,
    )


@pytest.fixture
def super_admin_user(db):
    """Super admin user."""
    from apps.base.enums import UserRole

    return User.objects.create_user(
        username="super_admin",
        email="super_admin@test.com",
        password="testpass123",
        first_name="Super",
        last_name="Admin",
        is_staff=True,
        is_superuser=True,
        role=UserRole.SUPER_ADMIN.value,
    )


# ---------------------------------------------------------------------------
# Authenticated client fixtures — APIClient pre-authenticated per role
# ---------------------------------------------------------------------------


@pytest.fixture
def api_client():
    """Unauthenticated API client — simulates anonymous requests."""
    return APIClient()


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
admin_client = super_admin_client  #: Admin-level access
