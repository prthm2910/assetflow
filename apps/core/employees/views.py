"""
apps/core/employees/views.py — ViewSets for Department and Employee.
"""

import logging

from django.db import models
from rest_framework import status
from rest_framework.decorators import action

from apps.base.constants import UserRole
from apps.base.response import error_response, success_response
from apps.base.viewsets import BaseViewSet
from apps.core.employees.models import Department, Employee
from apps.core.employees.serializers import (
    DepartmentListSerializer,
    DepartmentSerializer,
    EmployeeCreateSerializer,
    EmployeeListSerializer,
    EmployeeSearchSerializer,
    EmployeeSerializer,
)

logger = logging.getLogger(__name__)


class DepartmentViewSet(BaseViewSet):
    """
    Department management within an organization.

    - Super admin: full CRUD across all organizations
    - Org admin: full CRUD within their organization
    - Employee: read-only within their organization

    Permissions:
        - Read (GET): Any authenticated user in the org
        - Write (POST/PUT/PATCH/DELETE): Org admin + Super admin
    """

    lookup_field = "dept_id"
    lookup_value_regex = r"[\w]+"
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    queryset = Department.objects.all()

    write_roles = [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]

    def scope_for_employee(self, queryset):
        """Employee sees only their own department."""
        user = self.request.user
        employee = user.employee
        if employee and employee.department:
            return queryset.filter(id=employee.department.id)
        return queryset.none()

    def get_serializer_class(self):
        if self.action == "list":
            return DepartmentListSerializer
        return DepartmentSerializer

    @action(detail=True, methods=["get"], url_path="employees")
    def employees(self, request, dept_id=None):  # noqa: ARG001
        """List all employees in a department."""
        department = self.get_object()
        # Use EmployeeViewSet ordering fields (not DepartmentViewSet's)
        queryset = (
            Employee.objects.filter(department=department, is_deleted=False)
            .select_related("user", "department")
            .order_by(*EmployeeViewSet.ordering)
        )
        return self.paginated_response(queryset, EmployeeListSerializer)


class EmployeeViewSet(BaseViewSet):
    """
    Employee management within an organization.

    - Super admin: full CRUD across all organizations
    - Org admin: full CRUD within their organization
    - Employee: read-only within their organization

    Custom actions:
        - manager_chain: Get reporting chain up to root
        - direct_reports: Get direct reports
        - org_chart: Get nested org chart subtree
        - change_manager: Reassign reporting line

    Permissions:
        - Read (GET): Any authenticated user in the org
        - Write (POST/PUT/PATCH/DELETE): Org admin + Super admin
    """

    lookup_field = "employee_id"
    lookup_value_regex = r"[\w]+"
    ordering_fields = ["created_at", "designation", "join_date"]
    ordering = ["-created_at"]

    write_roles = [UserRole.SUPER_ADMIN, UserRole.ORG_ADMIN]

    def get_queryset(self):
        queryset = Employee.objects.select_related(
            "user", "department", "manager", "organization"
        )
        return self.scope_queryset(queryset)

    def scope_for_employee(self, queryset):
        """Employee sees only employees in their own department."""
        user = self.request.user
        employee = user.employee
        if employee and employee.department:
            return queryset.filter(department=employee.department)
        return queryset.none()

    def get_serializer_class(self):
        if self.action == "list":
            return EmployeeListSerializer
        if self.action == "create":
            return EmployeeCreateSerializer
        return EmployeeSerializer

    @action(detail=True, methods=["get"], url_path="manager-chain")
    def manager_chain(self, request, employee_id=None):
        """Get the full reporting chain from this employee up to the top."""
        employee = self.get_object()
        chain = employee.get_manager_chain()
        serializer = EmployeeListSerializer(chain, many=True)
        return success_response(
            data=serializer.data,
            message=f"Manager chain for {employee.user.get_full_name()}.",
        )

    @action(detail=True, methods=["get"], url_path="direct-reports")
    def direct_reports(self, request, employee_id=None):
        """Get direct reports of this employee."""
        employee = self.get_object()
        reports = Employee.objects.filter(manager=employee).active()
        return self.paginated_response(reports, EmployeeListSerializer)

    @action(detail=True, methods=["get"], url_path="org-chart")
    def org_chart(self, request, employee_id=None):
        """Get the nested org chart subtree rooted at this employee."""
        employee = self.get_object()
        tree = self._build_org_chart(employee)
        return success_response(data=tree)

    def _build_org_chart(self, employee):
        """Recursively build org chart tree."""
        children = []
        for report in employee.direct_reports.active():
            children.append(self._build_org_chart(report))
        return {
            "employee": EmployeeListSerializer(employee).data,
            "children": children,
        }

    @action(detail=True, methods=["post"], url_path="change-manager")
    def change_manager(self, request, employee_id=None):
        """Reassign this employee's manager."""
        employee = self.get_object()
        new_manager_id = request.data.get("manager_id")

        if new_manager_id is None:
            new_manager_id = request.data.get("manager")

        if new_manager_id is None:
            return error_response(
                message="manager_id is required.",
                code="VALIDATION_ERROR",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Prevent self-management
        if str(new_manager_id) == str(employee.id):
            logger.warning(
                "Self-management attempt for employee %s by %s",
                employee.employee_id,
                request.user.email,
            )
            return error_response(
                message="An employee cannot be their own manager.",
                code="VALIDATION_ERROR",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Validate manager belongs to same org
        try:
            new_manager = Employee.objects.get(id=new_manager_id, is_deleted=False)
        except Employee.DoesNotExist:
            return error_response(
                message="Manager not found.",
                code="NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if new_manager.organization != employee.organization:
            return error_response(
                message="Manager must belong to the same organization.",
                code="CROSS_TENANT",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Detect cycles
        if self._would_create_cycle(employee, new_manager):
            logger.warning(
                "Cycle detected: %s → %s by %s",
                employee.employee_id,
                new_manager.employee_id,
                request.user.email,
            )
            return error_response(
                message="Cannot set this manager — would create a reporting cycle.",
                code="CYCLE_DETECTED",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        employee.manager = new_manager
        employee.save(update_fields=["manager", "updated_at"])
        serializer = EmployeeSerializer(employee)
        logger.info(
            "Manager changed for %s to %s by %s",
            employee.user.get_full_name(),
            new_manager.user.get_full_name(),
            request.user.email,
        )
        return success_response(
            data=serializer.data,
            message=f"Manager changed to {new_manager.user.get_full_name()}.",
        )

    def _would_create_cycle(self, employee, new_manager):
        """Check if assigning new_manager would create a cycle."""
        seen = set()
        current = new_manager
        while current:
            if current.id == employee.id:
                return True
            if current.id in seen:
                break
            seen.add(current.id)
            current = current.manager
        return False

    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request):
        """
        Search employees by name, email, designation, or employee_id.
        Uses query param ?q=<search_term>
        """
        query = request.query_params.get("q", "").strip()
        if not query:
            return error_response(
                message="Query parameter 'q' is required.",
                code="VALIDATION_ERROR",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        base_qs = Employee.objects.filter(is_deleted=False).select_related(
            "user", "department", "organization"
        )

        if not getattr(user, "is_super_admin", False):
            user_org = getattr(user, "organization", None)
            if user_org:
                base_qs = base_qs.filter(organization=user_org)
            else:
                return success_response(data=[])

        results = base_qs.filter(
            models.Q(user__first_name__icontains=query)
            | models.Q(user__last_name__icontains=query)
            | models.Q(user__email__icontains=query)
            | models.Q(employee_id__icontains=query)
            | models.Q(designation__icontains=query)
        )[:20]

        logger.debug("Employee search '%s' returned %d results by %s", query, len(results), user.email)
        serializer = EmployeeSearchSerializer(results, many=True)
        return success_response(data=serializer.data)
