"""
apps/core/employees/urls.py — URL routing for departments and employees.

Included at /api/v1/employees/ from assetflow/urls.py.

Endpoints:
    Departments:
        GET|POST   /departments/           — list, create
        GET        /departments/{dept_id}/ — retrieve
        PUT|PATCH  /departments/{dept_id}/ — update, partial_update
        DELETE     /departments/{dept_id}/ — destroy
        GET        /departments/{dept_id}/employees/ — employees in dept

    Employees:
        GET|POST   /                        — list, create
        GET        /{employee_id}/          — retrieve
        PUT|PATCH  /{employee_id}/          — update, partial_update
        DELETE     /{employee_id}/          — destroy
        GET        /{employee_id}/manager-chain/
        GET        /{employee_id}/direct-reports/
        GET        /{employee_id}/org-chart/
        POST       /{employee_id}/change-manager/
        GET        /search/?q=<query>
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.core.employees.views import DepartmentViewSet, EmployeeViewSet


router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="departments")
router.register("", EmployeeViewSet, basename="employees")

urlpatterns = router.urls
