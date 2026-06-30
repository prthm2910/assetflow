"""
apps/base/response.py — Standardized API response helpers.

Provides consistent response envelope:
- success_response(): Wraps data in {success: true, data: ..., message: ...}
- error_response(): Wraps errors in {success: false, error: {code, message, details}}

Also provides custom exception handler for DRF.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def success_response(data=None, message="Success", status_code=status.HTTP_200_OK):
    """
    Return a standardized success response.

    Args:
        data: The response data (dict, list, or None).
        message: Human-readable success message.
        status_code: HTTP status code (default 200).

    Returns:
        Response with standardized envelope.
    """
    return Response(
        {
            "success": True,
            "data": data,
            "message": message,
        },
        status=status_code,
    )


def error_response(
    message="An error occurred",
    code="ERROR",
    details=None,
    status_code=status.HTTP_400_BAD_REQUEST,
):
    """
    Return a standardized error response.

    Args:
        message: Human-readable error message.
        code: Machine-readable error code.
        details: Additional error details (dict, list, or None).
        status_code: HTTP status code (default 400).

    Returns:
        Response with standardized error envelope.
    """
    error_payload = {
        "code": code,
        "message": message,
    }
    if details is not None:
        error_payload["details"] = details

    return Response(
        {
            "success": False,
            "error": error_payload,
        },
        status=status_code,
    )


def custom_exception_handler(exc, context):
    """
    Custom exception handler for DRF that wraps errors in the standard envelope.

    - Validation errors: 400 with details
    - Authentication errors: 401
    - Permission errors: 403
    - Not found: 404
    - Server errors: 500
    """
    response = exception_handler(exc, context)

    if response is not None:
        # Map status codes to error codes
        error_codes = {
            400: "VALIDATION_ERROR",
            401: "AUTHENTICATION_ERROR",
            403: "PERMISSION_DENIED",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            500: "INTERNAL_ERROR",
        }

        status_code = response.status_code
        error_code = error_codes.get(status_code, "ERROR")

        # Extract message from response data
        if isinstance(response.data, dict):
            if "detail" in response.data:
                message = str(response.data["detail"])
                details = None
            else:
                message = "Validation failed"
                details = response.data
        elif isinstance(response.data, list):
            message = response.data[0] if response.data else "An error occurred"
            details = response.data
        else:
            message = str(response.data)
            details = None

        response.data = {
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
            },
        }
        if details:
            response.data["error"]["details"] = details

    return response


# ==============================================================================
# Standard Response Mixin
# ==============================================================================

class StandardResponseMixin:
    """
    Auto-wraps all successful DRF responses in the standard envelope.

    DRF's ModelViewSet returns raw data dicts. This mixin intercepts in
    `finalize_response()` and wraps them as {success: true, data: ..., message: ...}.

    The message is derived from action + model name (e.g. "Asset listed successfully."),
    but can be overridden via `action_messages` on the ViewSet.

    Skips wrapping for:
    - 204 No Content (destroy — no body)
    - Error responses (already use error_response envelope)
    - Responses already containing "success" key (already wrapped)
    - Streaming responses (file downloads)

    Usage: Mix into any ViewSet. Eliminates ~50 lines of boilerplate per ViewSet.
    """

    # Default action → message template. Override in subclasses per model.
    action_messages = {
        "list": "{model} listed successfully.",
        "retrieve": "{model} retrieved successfully.",
        "create": "{model} created successfully.",
        "update": "{model} updated successfully.",
        "partial_update": "{model} updated successfully.",
        "destroy": "{model} deleted successfully.",
    }

    def _get_resource_name(self) -> str:
        """
        Derive a human-readable resource name from the queryset model.

        Falls back to the model's verbose_name (Django Meta option).
        """
        try:
            qs = getattr(self, "queryset", None)
            model = getattr(qs, "model", None)
            if model is None:
                sc = getattr(self, "serializer_class", None)
                if sc and hasattr(sc, "Meta"):
                    model = getattr(sc.Meta, "model", None)
            if model:
                return model._meta.verbose_name.title()
        except Exception:
            pass
        return "Record"

    def finalize_response(self, request, response, *args, **kwargs):
        if isinstance(response, Response):
            status_code = response.status_code
            data = response.data

            # Don't wrap: 204 (no body), errors (>=400), already-wrapped, or streaming
            if (
                status_code == status.HTTP_204_NO_CONTENT
                or status_code >= 400
                or isinstance(data, dict) and "success" in data
                or hasattr(response, "streaming_content")
            ):
                return super().finalize_response(request, response, *args, **kwargs)

            # Build contextual message
            action = getattr(self, "action", None)
            resource = self._get_resource_name()

            # Check for custom message override on the ViewSet
            custom_messages = getattr(self, "action_messages", {}) or {}
            template = custom_messages.get(action) if action else None
            if template is None:
                template = self.action_messages.get(action or "", "")

            message = template.format(model=resource) if template else ""

            response.data = {
                "success": True,
                "data": data,
                "message": message,
            }

        return super().finalize_response(request, response, *args, **kwargs)
