"""
apps/base/health.py — Liveness and readiness probes for production.

/health/ — Liveness: is the process alive? Always returns 200 if Django is running.
/ready/  — Readiness: can the app serve traffic? Checks DB, cache connectivity.

Load balancers use /health/ for basic health checks.
Orchestrators (Kubernetes, ECS) use /ready/ before routing traffic.
"""

import logging

from django.core.cache import cache
from django.db import connections
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Liveness probe — is the Django process alive and responding?

    Returns 200 always. If the process is dead, the load balancer gets
    a connection refused and removes the instance.

    Usage: GET /health/
    """
    return JsonResponse({"status": "ok"}, status=200)


def readiness_check(request):
    """
    Readiness probe — can this instance serve traffic?

    Checks:
    - Database connectivity (default connection)
    - Cache connectivity (set + get roundtrip)

    Returns 200 if all checks pass, 503 with error details if any fail.

    Usage: GET /ready/
    """
    errors = []

    # Database check
    try:
        conn = connections["default"]
        conn.ensure_connection()
    except Exception as exc:
        errors.append(f"database: {exc}")
        logger.error("Readiness check failed — database: %s", exc)

    # Cache check
    try:
        cache_key = "__health_check__"
        cache.set(cache_key, "ok", timeout=10)
        if cache.get(cache_key) != "ok":
            errors.append("cache: set/get mismatch")
            logger.error("Readiness check failed — cache set/get mismatch")
    except Exception as exc:
        errors.append(f"cache: {exc}")
        logger.error("Readiness check failed — cache: %s", exc)

    if errors:
        return JsonResponse(
            {"status": "unhealthy", "errors": errors},
            status=503,
        )

    return JsonResponse({"status": "ok"}, status=200)
