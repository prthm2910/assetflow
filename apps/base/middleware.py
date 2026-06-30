"""
apps/base/middleware.py — Request middleware and context-local helpers.

RequestMiddleware stores the current request.user and IP address in context-local
storage (async-safe via asgiref.local.Local) so they can be accessed in signals
(outside of request context).
"""

from asgiref.local import Local

# Context-local storage — safe under async, threaded, and sync WSGI workers.
# threading.local() leaks state across threads in gunicorn --threads and breaks
# under Django's async runserver. asgiref.local.Local uses contextvars internally.
_context = Local()


def get_current_request():
    """Get the current request object from context-local storage."""
    return getattr(_context, "request", None)


def get_current_user():
    """Get the current user from the current request."""
    request = get_current_request()
    if request and hasattr(request, "user"):
        return request.user
    return None


def get_current_ip():
    """Get the client IP address from the current request."""
    request = get_current_request()
    if request:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
    return None


def get_current_request_id():
    """Get the X-Request-ID for the current request (if set)."""
    request = get_current_request()
    if request:
        return getattr(request, "request_id", None)
    return None


class RequestMiddleware:
    """
    Middleware that stores request context in context-local storage.
    Guarantees cleanup of context-local storage even if exceptions occur.

    Uses asgiref.local.Local (contextvars-based) instead of threading.local()
    for async safety and correct behavior under gunicorn --threads.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _context.request = request
        try:
            response = self.get_response(request)
        finally:
            _context.request = None
        return response


class RequestIDMiddleware:
    """
    Middleware that generates a unique X-Request-ID for every request.

    If the client sends an X-Request-ID header, that value is used
    (useful for tracing across microservices). Otherwise a UUID is generated.

    The ID is:
    - Stored on request.request_id (for middleware downstream)
    - Returned in the response header X-Request-ID
    - Available via get_current_request_id() in signals/audit handlers
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        import uuid

        request_id = request.META.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())
        request.request_id = request_id
        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        return response
