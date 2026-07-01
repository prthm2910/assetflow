"""
apps/analytics/dashboard/urls.py — Dashboard URL configuration.
"""

from django.urls import path

from apps.analytics.dashboard.views import (
    AllocationDashboardView,
    AllocationVisualizationView,
    AssetDashboardView,
    AssetVisualizationView,
    DashboardSummaryView,
    IncidentDashboardView,
    IncidentVisualizationView,
    LicenseDashboardView,
    LicenseVisualizationView,
    RequestDashboardView,
    RequestVisualizationView,
    SummaryVisualizationView,
)

urlpatterns = [
    # JSON endpoints
    path("summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("assets/", AssetDashboardView.as_view(), name="dashboard-assets"),
    path("incidents/", IncidentDashboardView.as_view(), name="dashboard-incidents"),
    path("requests/", RequestDashboardView.as_view(), name="dashboard-requests"),
    path("licenses/", LicenseDashboardView.as_view(), name="dashboard-licenses"),
    path("allocations/", AllocationDashboardView.as_view(), name="dashboard-allocations"),
    # HTML visualization endpoints
    path("summary/visualize/", SummaryVisualizationView.as_view(), name="dashboard-summary-visualize"),
    path("assets/visualize/", AssetVisualizationView.as_view(), name="dashboard-assets-visualize"),
    path("incidents/visualize/", IncidentVisualizationView.as_view(), name="dashboard-incidents-visualize"),
    path("requests/visualize/", RequestVisualizationView.as_view(), name="dashboard-requests-visualize"),
    path("licenses/visualize/", LicenseVisualizationView.as_view(), name="dashboard-licenses-visualize"),
    path("allocations/visualize/", AllocationVisualizationView.as_view(), name="dashboard-allocations-visualize"),
]
