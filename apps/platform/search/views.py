"""
apps/platform/search/views.py — Global search across all major models.

One endpoint, top 5 results per type, with links to the dedicated per-app
search endpoints for full paginated browsing.

Endpoint:  GET /api/v1/search/?q=<term>[&type=assets,employees]
"""

from django.db.models import Q
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.assets.inventory.models import Asset
from apps.assets.requests.models import AssetRequest
from apps.base.response import error_response, success_response
from apps.core.employees.models import Employee
from apps.operations.incidents.models import Incident
from apps.operations.licenses.models import SoftwareLicense

from .serializers import (
    AssetSearchSerializer,
    EmployeeSearchSerializer,
    IncidentSearchSerializer,
    LicenseSearchSerializer,
    RequestSearchSerializer,
)

RESULT_LIMIT = 5

# Config for each searchable type — keeps the view clean and extensible.
SEARCH_CONFIG = {
    "assets": {
        "label": "Assets",
        "model": Asset,
        "fields": [
            "name__icontains",
            "asset_id__icontains",
            "serial_number__icontains",
            "description__icontains",
        ],
        "serializer": AssetSearchSerializer,
        "view_all_url_template": "/api/v1/assets/?search={query}",
    },
    "employees": {
        "label": "Employees",
        "model": Employee,
        "fields": [
            "employee_id__icontains",
            "user__first_name__icontains",
            "user__last_name__icontains",
            "designation__icontains",
        ],
        "serializer": EmployeeSearchSerializer,
        "view_all_url_template": "/api/v1/employees/?search={query}",
    },
    "requests": {
        "label": "Requests",
        "model": AssetRequest,
        "fields": [
            "req_id__icontains",
            "reason__icontains",
        ],
        "serializer": RequestSearchSerializer,
        "view_all_url_template": "/api/v1/requests/?search={query}",
    },
    "incidents": {
        "label": "Incidents",
        "model": Incident,
        "fields": [
            "inc_id__icontains",
            "title__icontains",
            "description__icontains",
        ],
        "serializer": IncidentSearchSerializer,
        "view_all_url_template": "/api/v1/incidents/?search={query}",
    },
    "licenses": {
        "label": "Licenses",
        "model": SoftwareLicense,
        "fields": [
            "lic_id__icontains",
            "software_name__icontains",
            "vendor__icontains",
        ],
        "serializer": LicenseSearchSerializer,
        "view_all_url_template": "/api/v1/licenses/?search={query}",
    },
}


class GlobalSearchView(APIView):
    """
    Search across assets, employees, requests, incidents, and licenses.

    Returns top 5 matches per type with a link to the full (paginated)
    per-app search results for deeper browsing.

    Examples:
        GET /api/v1/search/?q=printer
        GET /api/v1/search/?q=john&type=employees
        GET /api/v1/search/?q=laptop&type=assets,incidents
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Global search",
        description="Search across assets, employees, requests, incidents, and licenses. "
        "Returns top 5 results per type with view_all links to full paginated results.",
        parameters=[
            {
                "name": "q",
                "required": True,
                "type": "str",
                "in": "query",
                "description": "Search term",
            },
            {
                "name": "type",
                "required": False,
                "type": "str",
                "in": "query",
                "description": "Comma-separated types: assets,employees,requests,incidents,licenses",
            },
        ],
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return error_response(
                message="Query parameter 'q' is required.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        is_super_admin = getattr(user, "role", None) == "super_admin"

        # Parse optional type filter: ?type=assets,employees
        type_param = request.query_params.get("type", "")
        requested_types = (
            {t.strip() for t in type_param.split(",") if t.strip()}
            if type_param
            else None
        )

        results = []
        for key, config in SEARCH_CONFIG.items():
            if requested_types and key not in requested_types:
                continue

            # Build org-scoped Q filter
            q_filter = Q()
            for field in config["fields"]:
                q_filter |= Q(**{field: query})

            queryset = config["model"].objects.filter(q_filter)
            if not is_super_admin and hasattr(config["model"], "organization"):
                queryset = queryset.filter(organization=user.organization)

            total_count = queryset.count()
            top_items = queryset[:RESULT_LIMIT]

            results.append(
                {
                    "type": key,
                    "label": config["label"],
                    "count": total_count,
                    "results": config["serializer"](
                        top_items, many=True, context={"request": request}
                    ).data,
                    "view_all_url": config["view_all_url_template"].format(
                        query=query
                    ),
                }
            )

        return success_response(
            data={"query": query, "results": results},
            message="Search results retrieved successfully.",
        )
