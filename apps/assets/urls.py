"""
apps/assets/urls.py — Parent URL router for all Asset sub-apps.

    /api/v1/assets/categories/   → AssetCategory CRUD
    /api/v1/assets/inventory/    → Asset CRUD
    /api/v1/assets/allocations/  → Allocation CRUD + transfer / return
"""



# Child app routers — each registered with its own prefix
from apps.assets.categories.urls import urlpatterns as cat_urls
from apps.assets.inventory.urls import urlpatterns as inv_urls
from apps.assets.allocations.urls import urlpatterns as alloc_urls
from apps.assets.requests.urls import urlpatterns as req_urls


urlpatterns = cat_urls + inv_urls + alloc_urls + req_urls
