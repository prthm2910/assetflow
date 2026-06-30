"""
apps/core/employees/models.py — Department and Employee models.
"""

from django.conf import settings
from django.db import models

from apps.base.models import BaseModel


class Department(BaseModel):
    """
    Department within an organization.

    Inherits from BaseModel:
    - UUID primary key, org FK, created_at / updated_at / created_by / updated_by
    - is_active, is_deleted, deleted_at (soft delete)
    - Auto HRID via BaseModel.save()
    """

    _display_id_prefix = "DEPT"
    _display_id_field = "dept_id"

    # HRID — public API identifier (e.g., DEPT7K3M9)
    dept_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        help_text="Human-readable unique ID (auto-generated)",
    )

    # Organization FK
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="departments",
    )

    # Department identity
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    code = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Short department code (e.g., ENG, HR, FIN)",
    )

    # Hierarchy
    parent = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="sub_departments",
    )

    # Department head — points to an Employee, not another Department
    head = models.ForeignKey(
        "Employee",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="headed_departments",
        help_text="Employee who heads this department",
    )

    class Meta:
        db_table = "departments"
        verbose_name = "department"
        verbose_name_plural = "departments"
        ordering = ["name"]
        unique_together = [["organization", "name"]]
        indexes = [
            models.Index(fields=["organization", "name"]),
            models.Index(fields=["organization", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.dept_id})"


class Employee(BaseModel):
    """
    Employee profile — 1:1 with User.

    Each User who is an EMPLOYEE has exactly one Employee record.
    Supports self-referential manager hierarchy.

    Inherits from BaseModel:
    - UUID primary key, org FK, created_at / updated_at / created_by / updated_by
    - is_active, is_deleted, deleted_at (soft delete)
    - Auto HRID via BaseModel.save()
    """

    _display_id_prefix = "EMP"
    _display_id_field = "employee_id"

    # HRID
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        null=True,
        help_text="Human-readable unique ID (auto-generated)",
    )

    # Links
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="employees",
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )

    # Reporting hierarchy — self-referential FK
    manager = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="direct_reports",
        help_text="Direct manager of this employee",
    )

    # Employee details
    designation = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Job title / designation",
    )
    employee_number = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Internal employee number (e.g., EMP-001)",
    )
    join_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date the employee joined the organization",
    )
    termination_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date the employee left (for records)",
    )

    class Meta:
        db_table = "employees"
        verbose_name = "employee"
        verbose_name_plural = "employees"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["department"]),
            models.Index(fields=["manager"]),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"

    def get_manager_chain(self):
        """Return list of managers up the chain (bottom-up)."""
        chain = []
        current = self.manager
        seen = set()
        while current and current.id not in seen:
            seen.add(current.id)
            chain.append(current)
            current = current.manager
        return chain

    def get_direct_reports_tree(self):
        """Return nested tree of all reports under this employee."""
        children = []
        for report in self.direct_reports.active():
            children.append(
                {
                    "employee": report,
                    "children": report.get_direct_reports_tree(),
                }
            )
        return children
