"""
apps/core/employees/tests/test_models.py — Unit tests for Department and Employee models.
"""

import pytest
from django.contrib.auth import get_user_model


User = get_user_model()


@pytest.mark.django_db
class TestDepartmentModel:
    def test_department_created_with_org(self, organization):
        from apps.core.employees.models import Department

        dept = Department.objects.create(
            organization=organization,
            name="Engineering",
            code="ENG",
        )
        assert dept.pk is not None
        assert dept.dept_id is not None
        assert dept.dept_id.startswith("DEPT")
        assert dept.organization == organization
        assert dept.name == "Engineering"
        assert dept.code == "ENG"
        assert dept.is_active is True
        assert dept.is_deleted is False

    def test_department_unique_together_per_org(
        self, organization, second_organization
    ):
        from apps.core.employees.models import Department

        Department.objects.create(organization=organization, name="Engineering")
        # Same name in different org — allowed
        dept2 = Department.objects.create(
            organization=second_organization, name="Engineering"
        )
        assert dept2.pk is not None

    def test_department_unique_together_same_org_fails(self, organization):
        from django.db import IntegrityError
        from apps.core.employees.models import Department

        Department.objects.create(organization=organization, name="Engineering")
        with pytest.raises(IntegrityError):
            Department.objects.create(
                organization=organization, name="Engineering"
            )

    def test_department_soft_delete(self, department):
        department.delete()
        department.refresh_from_db()
        assert department.is_deleted is True
        assert department.deleted_at is not None

    def test_department_str(self, department):
        assert department.name in str(department)
        assert department.dept_id in str(department)


@pytest.mark.django_db
class TestEmployeeModel:
    def test_employee_created_with_user(self, organization, department):
        user = User.objects.create_user(
            username="john_doe",
            email="john@test.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
            organization=organization,
        )
        from apps.core.employees.models import Employee

        emp = Employee.objects.create(
            organization=organization,
            user=user,
            department=department,
            designation="Software Engineer",
        )
        assert emp.pk is not None
        assert emp.employee_id.startswith("EMP")
        assert emp.user == user
        assert emp.department == department
        assert emp.is_active is True

    def test_employee_user_one_to_one(self, organization, department):
        """One user can only have one employee profile."""
        from django.db import IntegrityError
        from apps.core.employees.models import Employee

        user = User.objects.create_user(
            username="unique_test",
            email="unique@test.com",
            password="testpass123",
            organization=organization,
        )
        Employee.objects.create(
            organization=organization,
            user=user,
            department=department,
        )
        with pytest.raises(IntegrityError):
            Employee.objects.create(
                organization=organization,
                user=user,
                department=department,
            )

    def test_employee_manager_chain(self, organization, department, manager_employee):
        from apps.core.employees.models import Employee

        emp_user = User.objects.create_user(
            username="chain_test",
            email="chain@test.com",
            password="testpass123",
            organization=organization,
        )
        emp = Employee.objects.create(
            organization=organization,
            user=emp_user,
            department=department,
            manager=manager_employee,
        )
        chain = emp.get_manager_chain()
        assert len(chain) == 1
        assert chain[0] == manager_employee

    def test_employee_manager_chain_no_manager(self, employee):
        chain = employee.get_manager_chain()
        assert chain == []

    def test_employee_soft_delete(self, employee):
        employee.delete()
        employee.refresh_from_db()
        assert employee.is_deleted is True
        assert employee.deleted_at is not None

    def test_employee_str(self, employee):
        assert employee.user.get_full_name() in str(employee)
        assert employee.employee_id in str(employee)

    def test_employee_direct_reports_tree(
        self, organization, department, manager_employee, employee_with_manager
    ):
        tree = manager_employee.get_direct_reports_tree()
        assert len(tree) == 1
        assert tree[0]["employee"] == employee_with_manager
        assert tree[0]["children"] == []
