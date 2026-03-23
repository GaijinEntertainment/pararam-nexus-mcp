"""Helper functions for creating ToolResponse objects."""

from typing import TypeVar

from pararam_nexus_mcp.models import ToolResponse

T = TypeVar('T')


def success_response[T](message: str, payload: T) -> ToolResponse[T]:
    """Create a successful ToolResponse.

    Args:
        message: Human-readable summary of the result
        payload: The actual response data

    Returns:
        ToolResponse with success=True and the provided payload
    """
    return ToolResponse(
        success=True,
        message=message,
        error=None,
        payload=payload,
    )


def error_response(message: str, error: str) -> ToolResponse[T | None]:
    """Create an error ToolResponse.

    Args:
        message: Human-readable summary of the error
        error: Detailed error message

    Returns:
        ToolResponse with success=False, the error message, and no payload.
        Can be used with any ToolResponse[T | None] return type.
    """
    return ToolResponse(
        success=False,
        message=message,
        error=error,
        payload=None,
    )
