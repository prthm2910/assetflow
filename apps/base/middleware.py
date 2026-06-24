"""
apps/base/middleware.py — Request middleware and thread-local helpers.

RequestMiddleware stores the current request.user and IP address in thread-local
storage so they can be accessed in signals (outside of request context).
"""
import threading
# Thread-local storage for request context
_thread_locals = threading.local()


def get_current_request():
    """Get the current request object from thread-local storage."""
    return getattr(_thread_locals, 'request', None)


def get_current_user():
    """Get the current user from the current request."""
    request = get_current_request()
    if request and hasattr(request, 'user'):
        return request.user
    return None


def get_current_ip():
    """Get the client IP address from the current request."""
    request = get_current_request()
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    return None


class RequestMiddleware:
    """
    Middleware that stores request context in thread-local storage.
    Guarantees cleanup of thread-local storage even if exceptions occur.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        try:
            response = self.get_response(request)
        finally:
            _thread_locals.request = None
        return response
