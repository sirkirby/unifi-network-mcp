"""Confirmation and preview utilities for mutating operations.

This module provides helpers for the preview-then-confirm pattern used by
mutating tools. When confirm=false, tools should return a preview of what
will happen, giving LLM agents context to make informed decisions.

Environment Variables:
    UNIFI_AUTO_CONFIRM: Set to "true" to skip confirmation previews and
        execute operations directly. Useful for workflow automation (n8n, etc.)
        where the two-step confirmation adds unnecessary complexity.
"""

import os
from typing import Any, Dict, List, Optional


def should_auto_confirm() -> bool:
    """Check if auto-confirm is enabled via environment variable.

    When UNIFI_AUTO_CONFIRM=true, tools should skip the preview step
    and execute operations directly, as if confirm=true was passed.

    This is useful for:
    - Workflow automation tools (n8n, Make, Zapier)
    - Scripted/batch operations
    - Environments where confirmation adds unnecessary friction

    Returns:
        True if auto-confirm is enabled, False otherwise.
    """
    return os.getenv("UNIFI_AUTO_CONFIRM", "").lower() in ("true", "1", "yes")


def preview_response(
    action: str,
    resource_type: str,
    resource_id: str,
    current_state: Dict[str, Any],
    proposed_changes: Dict[str, Any],
    resource_name: Optional[str] = None,
    warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a standardized preview response for confirm=false.

    Args:
        action: The action being performed (e.g., "toggle", "update", "create", "delete")
        resource_type: Type of resource (e.g., "port_forward", "firewall_rule")
        resource_id: Unique identifier of the resource
        current_state: Current state of relevant fields
        proposed_changes: What will change if confirmed
        resource_name: Human-readable name of the resource (optional)
        warnings: List of warning messages (optional)

    Returns:
        Standardized preview response dict

    Example:
        >>> preview_response(
        ...     action="toggle",
        ...     resource_type="port_forward",
        ...     resource_id="abc123",
        ...     current_state={"enabled": True, "name": "SSH"},
        ...     proposed_changes={"enabled": False},
        ...     resource_name="SSH Access"
        ... )
        {
            "success": False,
            "requires_confirmation": True,
            "action": "toggle",
            "resource_type": "port_forward",
            "resource_id": "abc123",
            "resource_name": "SSH Access",
            "preview": {
                "current": {"enabled": True, "name": "SSH"},
                "proposed": {"enabled": False}
            },
            "message": "Review the changes above. Set confirm=true to execute."
        }
    """
    response: Dict[str, Any] = {
        "success": False,
        "requires_confirmation": True,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "preview": {
            "current": current_state,
            "proposed": proposed_changes,
        },
        "message": "Review the changes above. Set confirm=true to execute.",
    }

    if resource_name:
        response["resource_name"] = resource_name

    if warnings:
        response["warnings"] = warnings

    return response


def toggle_preview(
    resource_type: str,
    resource_id: str,
    resource_name: Optional[str],
    current_enabled: bool,
    additional_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convenience helper for toggle operations.

    Args:
        resource_type: Type of resource being toggled
        resource_id: Unique identifier
        resource_name: Human-readable name
        current_enabled: Current enabled state
        additional_info: Extra fields to include in current state

    Returns:
        Preview response for toggle operation
    """
    current_state = {"enabled": current_enabled}
    if additional_info:
        current_state.update(additional_info)

    proposed = {"enabled": not current_enabled}
    new_state = "disabled" if current_enabled else "enabled"

    response = preview_response(
        action="toggle",
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        current_state=current_state,
        proposed_changes=proposed,
    )

    # Make the message more descriptive for toggles
    name_str = f"'{resource_name}'" if resource_name else resource_id
    response["message"] = f"Will {new_state} {resource_type} {name_str}. Set confirm=true to execute."

    return response


def update_preview(
    resource_type: str,
    resource_id: str,
    resource_name: Optional[str],
    current_state: Dict[str, Any],
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    """Convenience helper for update operations.

    Args:
        resource_type: Type of resource being updated
        resource_id: Unique identifier
        resource_name: Human-readable name
        current_state: Current values of fields being changed
        updates: New values being applied

    Returns:
        Preview response for update operation
    """
    # Filter current_state to only show fields being changed
    relevant_current = {k: current_state.get(k) for k in updates.keys()}

    response = preview_response(
        action="update",
        resource_type=resource_type,
        resource_id=resource_id,
        resource_name=resource_name,
        current_state=relevant_current,
        proposed_changes=updates,
    )

    # Make the message more descriptive
    name_str = f"'{resource_name}'" if resource_name else resource_id
    fields = ", ".join(updates.keys())
    response["message"] = f"Will update {fields} on {resource_type} {name_str}. Set confirm=true to execute."

    return response


def create_preview(
    resource_type: str,
    resource_data: Dict[str, Any],
    resource_name: Optional[str] = None,
    warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Convenience helper for create operations.

    Args:
        resource_type: Type of resource being created
        resource_data: The data that will be used to create the resource
        resource_name: Human-readable name if available
        warnings: Any warnings about the create operation

    Returns:
        Preview response for create operation
    """
    response: Dict[str, Any] = {
        "success": False,
        "requires_confirmation": True,
        "action": "create",
        "resource_type": resource_type,
        "preview": {
            "will_create": resource_data,
        },
        "message": f"Will create new {resource_type}. Set confirm=true to execute.",
    }

    if resource_name:
        response["resource_name"] = resource_name
        response["message"] = f"Will create {resource_type} '{resource_name}'. Set confirm=true to execute."

    if warnings:
        response["warnings"] = warnings

    return response
