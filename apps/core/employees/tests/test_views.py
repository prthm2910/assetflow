"""
apps/core/employees/tests/test_views.py — API tests for Department and Employee endpoints.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status


User = get_user_model()


# ==============================================================================
# Department ViewSet Tests
# ==============================================================================

@pytest.mark.django_db
class TestDepartmentViewSet:
    def test_list_departments_as_org_admin(self, org_admin_client, department):
        response = org_admin_client.get("/api/v1/employees/departments/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["results"]) == 1

    def test_list_departments_employee_readonly(self, employee_client, department):
        response = employee_client.get("/api/v1/employees/departments/")
        assert response.status_code == status.HTTP_200_OK

    def test_list_departments_excludes_other_org(self, employee_client, second_organization):
        from apps.core.employees.models import Department
        Department.objects.create(organization=second_organization, name="Other Org Dept")
        response = employee_client.get("/api/v1/employees/departments/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["results"]) == 0

    def test_list_departments_as_super_admin(self, super_admin_client, department, second_organization):
        from apps.core.employees.models import Department
        Department.objects.create(organization=second_organization, name="Other Org Dept")
        response = super_admin_client.get("/api/v1/employees/departments/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["results"]) == 2

    def test_create_department_as_org_admin(self, org_admin_client, organization):
        response = org_admin_client.post(
            "/api/v1/employees/departments/",
            {"name": "Sales", "code": "SAL", "organization": str(organization.id)},
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["data"]["name"] == "Sales"

    def test_create_department_as_employee_forbidden(self, employee_client, organization):
        response = employee_client.post(
            "/api/v1/employees/departments/",
            {"name": "Finance", "code": "FIN", "organization": str(organization.id)},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_duplicate_department_same_org_fails(self, org_admin_client, organization, department):
        response = org_admin_client.post(
            "/api/v1/employees/departments/",
            {"name": department.name, "organization": str(organization.id)},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_retrieve_department(self, org_admin_client, department):
        response = org_admin_client.get(
            f"/api/v1/employees/departments/{department.dept_id}/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["dept_id"] == department.dept_id

    def test_update_department_as_org_admin(self, org_admin_client, department):
        response = org_admin_client.patch(
            f"/api/v1/employees/departments/{department.dept_id}/",
            {"description": "Updated description"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["description"] == "Updated description"

    def test_delete_department_soft_deletes(self, org_admin_client, department):
        response = org_admin_client.delete(
            f"/api/v1/employees/departments/{department.dept_id}/"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        department.refresh_from_db()
        assert department.is_deleted is True

    def test_department_employees_action(self, org_admin_client, department, employee):
        response = org_admin_client.get(
            f"/api/v1/employees/departments/{department.dept_id}/employees/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["results"]) == 1

    def test_anonymous_cannot_list_departments(self, api_client, department):
        response = api_client.get("/api/v1/employees/departments/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==============================================================================
# Employee ViewSet Tests
# ==============================================================================

@pytest.mark.django_db
class TestEmployeeViewSet:
    def test_list_employees_as_org_admin(self, org_admin_client, employee):
        response = org_admin_client.get("/api/v1/employees/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["results"]) == 1

    def test_list_employees_excludes_other_org(self, org_admin_client, second_organization):
        from apps.core.employees.models import Employee
        user = User.objects.create_user(
            username="other_emp", email="other@test.com", password="testpass123",
            organization=second_organization,
        )
        Employee.objects.create(organization=second_organization, user=user)
        response = org_admin_client.get("/api/v1/employees/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["results"]) == 0

    def test_list_employees_as_super_admin(self, super_admin_client, employee, second_organization):
        from apps.core.employees.models import Employee
        user = User.objects.create_user(
            username="super_other", email="super_other@test.com", password="testpass123",
            organization=second_organization,
        )
        Employee.objects.create(organization=second_organization, user=user)
        response = super_admin_client.get("/api/v1/employees/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()["results"]) == 2

    def test_create_employee(self, org_admin_client, organization, department):
        user = User.objects.create_user(
            username="new_emp_test", email="newemp@test.com", password="testpass123",
            first_name="New", last_name="Employee", organization=organization,
        )
        response = org_admin_client.post(
            "/api/v1/employees/",
            {
                "user": user.id,
                "organization": str(organization.id),
                "department": str(department.id),
                "designation": "QA Engineer",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["data"]["designation"] == "QA Engineer"

    def test_create_employee_no_duplicate_profile(self, org_admin_client, organization, department, employee):
        response = org_admin_client.post(
            "/api/v1/employees/",
            {
                "user": employee.user.id,
                "organization": str(organization.id),
                "department": str(department.id),
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_employee_cross_tenant_fails(self, org_admin_client, second_organization, org_admin_user):
        from apps.core.employees.models import Department
        dept = Department.objects.create(
            organization=second_organization, name="Other Dept",
        )
        response = org_admin_client.post(
            "/api/v1/employees/",
            {
                "user": org_admin_user.id,
                "organization": str(second_organization.id),
                "department": str(dept.id),
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_employee_as_employee_forbidden(self, employee_client, organization, department):
        user = User.objects.create_user(
            username="emp_forbid", email="empforbid@test.com", password="testpass123",
            organization=organization,
        )
        response = employee_client.post(
            "/api/v1/employees/",
            {
                "user": user.id,
                "organization": str(organization.id),
                "department": str(department.id),
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_employee(self, org_admin_client, employee):
        response = org_admin_client.get(
            f"/api/v1/employees/{employee.employee_id}/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["employee_id"] == employee.employee_id

    def test_update_employee(self, org_admin_client, employee):
        response = org_admin_client.patch(
            f"/api/v1/employees/{employee.employee_id}/",
            {"designation": "Senior Engineer"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"]["designation"] == "Senior Engineer"

    def test_delete_employee_soft_deletes(self, org_admin_client, employee):
        response = org_admin_client.delete(
            f"/api/v1/employees/{employee.employee_id}/"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        employee.refresh_from_db()
        assert employee.is_deleted is True

    def test_anonymous_cannot_list_employees(self, api_client, employee):
        response = api_client.get("/api/v1/employees/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==============================================================================
# Employee Custom Action Tests
# ==============================================================================

@pytest.mark.django_db
class TestEmployeeCustomActions:
    def test_manager_chain(self, org_admin_client, employee_with_manager):
        response = org_admin_client.get(
            f"/api/v1/employees/{employee_with_manager.employee_id}/manager-chain/"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert len(data) == 1
        assert data[0]["id"] == str(employee_with_manager.manager.id)

    def test_manager_chain_no_manager(self, org_admin_client, employee):
        response = org_admin_client.get(
            f"/api/v1/employees/{employee.employee_id}/manager-chain/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["data"] == []

    def test_direct_reports(self, org_admin_client, manager_employee, employee_with_manager):
        response = org_admin_client.get(
            f"/api/v1/employees/{manager_employee.employee_id}/direct-reports/"
        )
        assert response.status_code == status.HTTP_200_OK
        results = response.json()["results"]
        assert len(results) == 1
        assert results[0]["id"] == str(employee_with_manager.id)

    def test_direct_reports_none(self, org_admin_client, employee):
        response = org_admin_client.get(
            f"/api/v1/employees/{employee.employee_id}/direct-reports/"
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["results"] == []

    def test_org_chart(self, org_admin_client, manager_employee, employee_with_manager):
        response = org_admin_client.get(
            f"/api/v1/employees/{manager_employee.employee_id}/org-chart/"
        )
        assert response.status_code == status.HTTP_200_OK
        tree = response.json()["data"]
        assert tree["employee"]["id"] == str(manager_employee.id)
        assert len(tree["children"]) == 1
        assert tree["children"][0]["employee"]["id"] == str(employee_with_manager.id)

    def test_change_manager(self, org_admin_client, employee, manager_employee, organization):
        from apps.core.employees.models import Employee
        new_manager_user = User.objects.create_user(
            username="new_mgr", email="new_mgr@test.com", password="testpass123",
            organization=organization,
        )
        new_manager = Employee.objects.create(
            organization=organization, user=new_manager_user,
        )
        response = org_admin_client.post(
            f"/api/v1/employees/{employee.employee_id}/change-manager/",
            {"manager_id": str(new_manager.id)},
        )
        assert response.status_code == status.HTTP_200_OK
        employee.refresh_from_db()
        assert employee.manager == new_manager

    def test_change_manager_self_forbidden(self, org_admin_client, employee):
        response = org_admin_client.post(
            f"/api/v1/employees/{employee.employee_id}/change-manager/",
            {"manager_id": str(employee.id)},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_change_manager_cross_org_fails(self, org_admin_client, employee, second_organization):
        from apps.core.employees.models import Employee
        cross_org_user = User.objects.create_user(
            username="cross_mgr", email="cross_mgr@test.com", password="testpass123",
            organization=second_organization,
        )
        cross_manager = Employee.objects.create(
            organization=second_organization, user=cross_org_user,
        )
        response = org_admin_client.post(
            f"/api/v1/employees/{employee.employee_id}/change-manager/",
            {"manager_id": str(cross_manager.id)},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "CROSS_TENANT"

    def test_change_manager_missing_id(self, org_admin_client, employee):
        response = org_admin_client.post(
            f"/api/v1/employees/{employee.employee_id}/change-manager/", {}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_manager_cycle_prevention(self, org_admin_client, manager_employee, employee_with_manager):
        response = org_admin_client.post(
            f"/api/v1/employees/{manager_employee.employee_id}/change-manager/",
            {"manager_id": str(employee_with_manager.id)},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error"]["code"] == "CYCLE_DETECTED"

    def test_search_employees(self, org_admin_client, employee):
        response = org_admin_client.get(
            f"/api/v1/employees/search/?q={employee.user.first_name}"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert len(data) >= 1

    def test_search_employees_by_email(self, org_admin_client, employee):
        response = org_admin_client.get(
            f"/api/v1/employees/search/?q={employee.user.email}"
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert len(data) >= 1

    def test_search_employees_no_query(self, org_admin_client):
        response = org_admin_client.get("/api/v1/employees/search/")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_search_excludes_other_org(self, org_admin_client, second_organization):
        from apps.core.employees.models import Employee
        user = User.objects.create_user(
            username="other_search", email="other_search@test.com", password="testpass123",
            first_name="Other", organization=second_organization,
        )
        Employee.objects.create(organization=second_organization, user=user)
        response = org_admin_client.get("/api/v1/employees/search/?q=Other")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert len(data) == 0

    def test_search_super_admin_sees_all_orgs(self, super_admin_client, second_organization):
        from apps.core.employees.models import Employee
        user = User.objects.create_user(
            username="super_search", email="super_search@test.com",
            first_name="SuperSearch", password="testpass123",
            organization=second_organization,
        )
        Employee.objects.create(organization=second_organization, user=user)
        response = super_admin_client.get("/api/v1/employees/search/?q=SuperSearch")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()["data"]
        assert len(data) == 1
