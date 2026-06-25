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


@pytest.fixture
def second_organization(transactional_db):
    """Create a second test organization (for cross-tenant tests)."""
    from apps.core.organizations.models import Organization

    return Organization.objects.create(
        name="Second Org",
        slug="second-org",
        contact_email="admin@secondorg.com",
        contact_phone="+9876543210",
        address="456 Second St",
        city="Secondville",
        country="Secondland",
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
    from apps.base.constants import UserRole

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
    from apps.base.constants import UserRole

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


@pytest.fixture
def second_org_user(transactional_db, second_organization):
    """User belonging to the second organization (for cross-tenant tests)."""
    return User.objects.create_user(
        username="second_emp",
        email="second_emp@test.com",
        password="testpass123",
        first_name="Second",
        last_name="Employee",
        role="employee",
        organization_id=second_organization.id,
    )


# ---------------------------------------------------------------------------
# Department fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def department(transactional_db, organization):
    """Create a test department within the organization."""
    from apps.core.employees.models import Department

    return Department.objects.create(
        organization=organization,
        name="Engineering",
        code="ENG",
        description="Software engineering department",
    )


@pytest.fixture
def second_department(transactional_db, organization):
    """Create a second department within the organization."""
    from apps.core.employees.models import Department

    return Department.objects.create(
        organization=organization,
        name="Human Resources",
        code="HR",
        description="HR department",
    )


@pytest.fixture
def sub_department(transactional_db, organization, department):
    """Create a sub-department under the main department."""
    from apps.core.employees.models import Department

    return Department.objects.create(
        organization=organization,
        name="Backend Team",
        code="ENG-BE",
        description="Backend engineering team",
        parent=department,
    )


# ---------------------------------------------------------------------------
# Employee fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def employee(transactional_db, organization, user, department):
    """Create an employee linked to the user and department."""
    from apps.core.employees.models import Employee

    return Employee.objects.create(
        organization=organization,
        user=user,
        department=department,
        designation="Software Engineer",
        employee_number="EMP-001",
    )


@pytest.fixture
def org_admin_employee(transactional_db, organization, org_admin_user, department):
    """Create an employee profile for the org admin user."""
    from apps.core.employees.models import Employee

    return Employee.objects.create(
        organization=organization,
        user=org_admin_user,
        department=department,
        designation="Organization Admin",
        employee_number="EMP-002",
    )


@pytest.fixture
def manager_employee(transactional_db, organization, department):
    """Create a manager employee (no user fixture — user created inline)."""
    from apps.core.employees.models import Employee

    manager_user = User.objects.create_user(
        username="manager",
        email="manager@test.com",
        password="testpass123",
        first_name="The",
        last_name="Manager",
        role="employee",
        organization_id=organization.id,
    )
    return Employee.objects.create(
        organization=organization,
        user=manager_user,
        department=department,
        designation="Engineering Manager",
        employee_number="EMP-MGR-001",
    )


@pytest.fixture
def employee_with_manager(
    transactional_db, organization, department, manager_employee
):
    """Create an employee who reports to the manager employee."""
    from apps.core.employees.models import Employee

    emp_user = User.objects.create_user(
        username="report_emp",
        email="report@test.com",
        password="testpass123",
        first_name="Report",
        last_name="Employee",
        role="employee",
        organization_id=organization.id,
    )
    return Employee.objects.create(
        organization=organization,
        user=emp_user,
        department=department,
        manager=manager_employee,
        designation="Junior Engineer",
        employee_number="EMP-003",
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
