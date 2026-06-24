"""
apps/base/pagination.py — Standard pagination for the API.
"""

from rest_framework.pagination import PageNumberPagination


class StandardPagePagination(PageNumberPagination):
    """
    Standard pagination for all list endpoints.

    Supports:
    - page: Page number (default)
    - page_size: Items per page (default 20, max 100)

    Response format:
    {
        "count": 150,
        "next": "/api/v1/resource/?page=2",
        "previous": null,
        "results": [...]
    }
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
