"""apps/operations/licenses/filters.py — FilterSet for licenses."""

import django_filters

from apps.base.filters import BaseFilterSet
from apps.operations.licenses.models import SoftwareLicense, LicenseAssignment


class SoftwareLicenseFilterSet(BaseFilterSet):
    """FilterSet for SoftwareLicense with HRID, type, and expiry filters."""

    lic_id = django_filters.CharFilter(
        field_name="lic_id",
        label="License HRID (e.g. LIC7K3M9)",
    )
    expiring_before = django_filters.DateFilter(
        field_name="expiry_date",
        lookup_expr="lte",
        label="Expiring before date",
    )

    class Meta:
        model = SoftwareLicense
        fields = ["lic_id", "license_type", "expiring_before"]


class LicenseAssignmentFilterSet(BaseFilterSet):
    """FilterSet for LicenseAssignment."""

    license_id = django_filters.CharFilter(
        field_name="license__lic_id",
        label="License HRID",
    )
    employee_id = django_filters.CharFilter(
        field_name="employee__employee_id",
        label="Employee HRID",
    )
    is_active = django_filters.BooleanFilter(
        field_name="revoked_at",
        lookup_expr="isnull",
        label="Active assignments only",
    )

    class Meta:
        model = LicenseAssignment
        fields = ["license_id", "employee_id", "is_active"]
