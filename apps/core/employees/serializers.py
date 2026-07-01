"""
apps/core/employees/serializers.py — Serializers for Department and Employee.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.base.serializers import BaseSerializer
from apps.core.employees.models import Department, Employee


def _get_active_employee_count(department):
    return department.employees.active().count()


User = get_user_model()


def _validate_employee_org(attrs: dict) -> None:
    """Shared cross-tenant check: employee user must belong to same org."""
    user = attrs.get("user")
    organization = attrs.get("organization")
    if user and organization:
        if user.organization and user.organization != organization:
            raise serializers.ValidationError(
                {"user": "The selected user does not belong to this organization."}
            )


class DepartmentSerializer(BaseSerializer):
    """Serializer for Department model."""

    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            "dept_id",
            "name",
            "code",
            "description",
            "organization",
            "parent",
            "head",
            "employee_count",
        ]
        read_only_fields = [
            "dept_id",
        ]

    def get_employee_count(self, obj):
        return _get_active_employee_count(obj)


class DepartmentListSerializer(BaseSerializer):
    """Lightweight department serializer for list views."""

    employee_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            "dept_id",
            "name",
            "code",
            "organization",
            "employee_count",
        ]

    def get_employee_count(self, obj):
        return _get_active_employee_count(obj)


class EmployeeSerializer(BaseSerializer):
    """Full employee serializer with user and manager details."""

    user_details = serializers.SerializerMethodField()
    department_name = serializers.CharField(source="department.name", read_only=True)
    manager_name = serializers.SerializerMethodField()
    direct_report_count = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "employee_id",
            "user",
            "user_details",
            "organization",
            "department",
            "department_name",
            "manager",
            "manager_name",
            "designation",
            "employee_number",
            "join_date",
            "termination_date",
            "direct_report_count",
        ]
        read_only_fields = [
            "employee_id",
        ]

    def get_user_details(self, obj):
        return {
            "user_id": obj.user.user_id,
            "email": obj.user.email,
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
            "role": obj.user.role,
            "phone": str(obj.user.phone) if obj.user.phone else None,
        }

    def get_manager_name(self, obj):
        if obj.manager:
            return obj.manager.user.get_full_name()
        return None

    def get_direct_report_count(self, obj):
        return obj.direct_reports.active().count()

    def validate(self, attrs: dict) -> dict:
        """Cross-tenant prevention: employee must belong to same org as user."""
        _validate_employee_org(attrs)
        return attrs


class EmployeeCreateSerializer(BaseSerializer):
    """Serializer for creating an Employee — couples to existing User."""

    class Meta:
        model = Employee
        fields = [
            "employee_id",
            "user",
            "organization",
            "department",
            "manager",
            "designation",
            "employee_number",
            "join_date",
            "termination_date",
        ]
        read_only_fields = [
            "employee_id",
        ]

    def validate_user(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Cannot create employee from inactive user.")
        if hasattr(value, "employee_profile") and value.employee_profile:
            raise serializers.ValidationError(
                "This user already has an employee profile."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        _validate_employee_org(attrs)
        # Prevent self-management (skip on create where instance is None)
        manager = attrs.get("manager")
        instance = getattr(self, "instance", None)
        if instance and manager == instance:
            raise serializers.ValidationError(
                {"manager": "An employee cannot be their own manager."}
            )
        return attrs


class EmployeeListSerializer(BaseSerializer):
    """Lightweight employee serializer for list views."""

    full_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source="department.name", read_only=True)
    designation = serializers.CharField(read_only=True)

    class Meta:
        model = Employee
        fields = [
            "employee_id",
            "full_name",
            "designation",
            "department",
            "department_name",
            "organization",
            "join_date",
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.email


class EmployeeSearchSerializer(serializers.Serializer):
    """Dedicated search serializer — not tied to a model."""

    employee_id = serializers.CharField(read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    designation = serializers.CharField(read_only=True)
    department = serializers.CharField(source="department.name", read_only=True)
    organization = serializers.CharField(source="organization.name", read_only=True)
    manager = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.email

    def get_email(self, obj):
        return obj.user.email

    def get_manager(self, obj):
        if obj.manager:
            return {
                "employee_id": obj.manager.employee_id,
                "name": obj.manager.user.get_full_name(),
            }
        return None
