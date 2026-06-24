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
