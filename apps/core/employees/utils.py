"""
apps/core/employees/utils.py — Utility functions for employees app.
"""

from collections import defaultdict

from apps.core.employees.serializers import EmployeeListSerializer


def build_org_chart_tree(employees: list, root_employee_id: str) -> dict:
    """
    Build a nested org chart tree from a flat list of employees.

    Args:
        employees: Flat list of Employee objects (pre-fetched from DB)
        root_employee_id: UUID of the root employee for the tree

    Returns:
        Nested dict with 'employee' and 'children' keys
    """
    # Build in-memory adjacency map: manager_id -> [children]
    children_map: dict = defaultdict(list)
    employee_map: dict = {}

    for emp in employees:
        employee_map[emp.id] = emp
        if emp.manager_id:
            children_map[emp.manager_id].append(emp)

    def _build_tree(emp):
        return {
            "employee": EmployeeListSerializer(emp).data,
            "children": [
                _build_tree(child) for child in children_map.get(emp.id, [])
            ],
        }

    root = employee_map.get(root_employee_id)
    if root is None:
        return {"employee": None, "children": []}
    return _build_tree(root)
