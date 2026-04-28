"""Standardized tool response formatting."""

from typing import Any


def success_response(data: Any = None, **kwargs) -> dict[str, Any]:
    result = {"success": True}
    if data is not None:
        result["data"] = data
    result.update(kwargs)
    return result


def error_response(error: str, **kwargs) -> dict[str, Any]:
    result = {"success": False, "error": error}
    result.update(kwargs)
    return result
