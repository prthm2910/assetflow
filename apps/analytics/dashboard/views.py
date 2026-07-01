"""
apps/analytics/dashboard/views.py — Dashboard stat endpoints.

Inherits from reusable base classes in apps.base.viewsets:
- BaseOrgAPIView for JSON endpoints
- BaseOrgTemplateView for HTML chart pages

Dashboard-specific: BaseDashboardView adds visualization_url logic.
"""

from django.urls import reverse
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status

from apps.base.response import success_response
from apps.base.viewsets import BaseOrgAPIView, BaseOrgTemplateView

from apps.analytics.dashboard.serializers import (
    AllocationDashboardSerializer,
    AssetDashboardSerializer,
    DashboardSummarySerializer,
    IncidentDashboardSerializer,
    LicenseDashboardSerializer,
    RequestDashboardSerializer,
)
from apps.analytics.dashboard.services import (
    AllocationRepository,
    AssetRepository,
    DashboardSummaryService,
    IncidentRepository,
    LicenseRepository,
    RequestRepository,
)


def _org_param():
    """Shared OpenAPI parameter for organization_id filtering."""
    return [
        OpenApiParameter(
            name="organization_id",
            description="Filter by organization (super admin only).",
            required=False,
            type=str,
        ),
    ]


class BaseDashboardView(BaseOrgAPIView):
    """Base for JSON dashboard endpoints.

    Extends BaseOrgAPIView with visualization_url support.
    Subclasses set ``viz_url_name`` and override ``get_data(org)``.
    """

    viz_url_name = None

    def get_data(self, org):
        """Override in subclass — return the data dict for this dashboard type."""
        raise NotImplementedError

    def get(self, request, *args, **kwargs):
        org, error = self.get_organization_or_error(request)
        if error:
            return error

        data = self.get_data(org)
        if self.viz_url_name:
            url = reverse(self.viz_url_name)
            org_id = request.query_params.get("organization_id")
            if org_id:
                url = f"{url}?organization_id={org_id}"
            data["visualization_url"] = request.build_absolute_uri(url)
        return success_response(data=data, message=self.get_message())


# ==============================================================================
# JSON Dashboard Views
# ==============================================================================


class DashboardSummaryView(BaseDashboardView):
    """Aggregated stats across all modules in a single call."""

    viz_url_name = "dashboard-summary-visualize"

    @extend_schema(
        responses={200: DashboardSummarySerializer},
        parameters=_org_param(),
        summary="Dashboard summary",
        description="Return high-level counts across all modules.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_data(self, org):
        return DashboardSummaryService.get_summary(org)

    def get_message(self):
        return "Dashboard summary retrieved successfully."


class AssetDashboardView(BaseDashboardView):
    """Asset-specific dashboard: status/category breakdown + utilization."""

    viz_url_name = "dashboard-assets-visualize"

    @extend_schema(
        responses={200: AssetDashboardSerializer},
        parameters=_org_param(),
        summary="Asset dashboard",
        description="Asset stats including status breakdown, category breakdown, and utilization rate.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_data(self, org):
        return {
            "total_assets": AssetRepository.get_total_count(org),
            "status_breakdown": AssetRepository.get_status_breakdown(org),
            "category_breakdown": AssetRepository.get_category_breakdown(org),
            "utilization_rate": AssetRepository.get_utilization_rate(org),
        }

    def get_message(self):
        return "Asset dashboard retrieved successfully."


class IncidentDashboardView(BaseDashboardView):
    """Incident-specific dashboard: status/category breakdown."""

    viz_url_name = "dashboard-incidents-visualize"

    @extend_schema(
        responses={200: IncidentDashboardSerializer},
        parameters=_org_param(),
        summary="Incident dashboard",
        description="Incident stats including status and category breakdown.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_data(self, org):
        return {
            "total_incidents": IncidentRepository.get_total_count(org),
            "status_breakdown": IncidentRepository.get_status_breakdown(org),
            "category_breakdown": IncidentRepository.get_category_breakdown(org),
        }

    def get_message(self):
        return "Incident dashboard retrieved successfully."


class RequestDashboardView(BaseDashboardView):
    """Request-specific dashboard: status breakdown."""

    viz_url_name = "dashboard-requests-visualize"

    @extend_schema(
        responses={200: RequestDashboardSerializer},
        parameters=_org_param(),
        summary="Request dashboard",
        description="Asset request stats including status breakdown.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_data(self, org):
        return {
            "total_requests": RequestRepository.get_total_count(org),
            "status_breakdown": RequestRepository.get_status_breakdown(org),
        }

    def get_message(self):
        return "Request dashboard retrieved successfully."


class LicenseDashboardView(BaseDashboardView):
    """License-specific dashboard: type breakdown + seat utilization."""

    viz_url_name = "dashboard-licenses-visualize"

    @extend_schema(
        responses={200: LicenseDashboardSerializer},
        parameters=_org_param(),
        summary="License dashboard",
        description="License stats including type breakdown, seat utilization, and expiring licenses.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_data(self, org):
        return {
            "total_licenses": LicenseRepository.get_total_count(org),
            "type_breakdown": LicenseRepository.get_type_breakdown(org),
            "total_seats": LicenseRepository.get_total_seats(org),
            "used_seats": LicenseRepository.get_used_seats(org),
            "utilization_rate": LicenseRepository.get_license_utilization_rate(org),
            "expiring_soon": LicenseRepository.get_expiring_soon(org),
        }

    def get_message(self):
        return "License dashboard retrieved successfully."


class AllocationDashboardView(BaseDashboardView):
    """Allocation-specific dashboard: active vs returned totals."""

    viz_url_name = "dashboard-allocations-visualize"

    @extend_schema(
        responses={200: AllocationDashboardSerializer},
        parameters=_org_param(),
        summary="Allocation dashboard",
        description="Allocation stats including active and returned counts.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_data(self, org):
        return {
            "total_allocations": AllocationRepository.get_total_count(org),
            "active": AllocationRepository.get_active_count(org),
            "returned": AllocationRepository.get_returned_count(org),
        }

    def get_message(self):
        return "Allocation dashboard retrieved successfully."


# ==============================================================================
# HTML Visualization Views (Chart.js)
# ==============================================================================


class SummaryVisualizationView(BaseOrgTemplateView):
    """HTML page showing all dashboard charts."""
    template_name = "dashboard/summary_chart.html"

    def get_context_data(self, org):
        summary = DashboardSummaryService.get_summary(org)
        ctx = {"summary": summary}

        ctx["asset_status_labels"] = [s["status"] for s in summary.get("assets", {}).get("status_breakdown", [])]
        ctx["asset_status_data"] = [s["count"] for s in summary.get("assets", {}).get("status_breakdown", [])]
        inc = summary.get("incidents", {}).get("status_breakdown", [])
        ctx["incident_status_labels"] = [s["status"] for s in inc]
        ctx["incident_status_data"] = [s["count"] for s in inc]
        req = summary.get("requests", {}).get("status_breakdown", [])
        ctx["request_status_labels"] = [s["status"] for s in req]
        ctx["request_status_data"] = [s["count"] for s in req]
        lic = summary.get("licenses", {}).get("type_breakdown", [])
        ctx["license_type_labels"] = [s["license_type"] for s in lic]
        ctx["license_type_data"] = [s["count"] for s in lic]
        return ctx


class AssetVisualizationView(BaseOrgTemplateView):
    """HTML page with asset charts."""
    template_name = "dashboard/assets_chart.html"

    def get_context_data(self, org):
        return {
            "data": {
                "total_assets": AssetRepository.get_total_count(org),
                "utilization_rate": AssetRepository.get_utilization_rate(org),
            },
            "status_breakdown": AssetRepository.get_status_breakdown(org),
            "category_breakdown": AssetRepository.get_category_breakdown(org),
        }


class IncidentVisualizationView(BaseOrgTemplateView):
    """HTML page with incident charts."""
    template_name = "dashboard/incidents_chart.html"

    def get_context_data(self, org):
        breakdown = IncidentRepository.get_status_breakdown(org)
        cat = IncidentRepository.get_category_breakdown(org)
        return {
            "data": {"total_incidents": IncidentRepository.get_total_count(org)},
            "open_count": IncidentRepository.get_open_count(org),
            "resolved_count": IncidentRepository.get_resolved_count(org),
            "status_labels": [s["status"] for s in breakdown],
            "status_data": [s["count"] for s in breakdown],
            "category_labels": [s["category"] for s in cat],
            "category_data": [s["count"] for s in cat],
        }


class RequestVisualizationView(BaseOrgTemplateView):
    """HTML page with request charts."""
    template_name = "dashboard/requests_chart.html"

    def get_context_data(self, org):
        breakdown = RequestRepository.get_status_breakdown(org)
        return {
            "data": {"total_requests": RequestRepository.get_total_count(org)},
            "pending_count": RequestRepository.get_pending_count(org),
            "approved_count": RequestRepository.get_approved_count(org),
            "rejected_count": RequestRepository.get_rejected_count(org),
            "status_labels": [s["status"] for s in breakdown],
            "status_data": [s["count"] for s in breakdown],
        }


class LicenseVisualizationView(BaseOrgTemplateView):
    """HTML page with license charts."""
    template_name = "dashboard/licenses_chart.html"

    def get_context_data(self, org):
        breakdown = LicenseRepository.get_type_breakdown(org)
        return {
            "data": {
                "total_licenses": LicenseRepository.get_total_count(org),
                "total_seats": LicenseRepository.get_total_seats(org),
                "used_seats": LicenseRepository.get_used_seats(org),
                "utilization_rate": LicenseRepository.get_license_utilization_rate(org),
                "expiring_soon": LicenseRepository.get_expiring_soon(org),
            },
            "type_labels": [s["license_type"] for s in breakdown],
            "type_data": [s["count"] for s in breakdown],
        }


class AllocationVisualizationView(BaseOrgTemplateView):
    """HTML page with allocation charts."""
    template_name = "dashboard/allocations_chart.html"

    def get_context_data(self, org):
        return {
            "data": {
                "total_allocations": AllocationRepository.get_total_count(org),
                "active": AllocationRepository.get_active_count(org),
                "returned": AllocationRepository.get_returned_count(org),
            },
        }
