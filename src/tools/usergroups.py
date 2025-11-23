"""User Group tools for UniFi Network MCP server.

Provides MCP tools for managing user groups and their bandwidth limits.
User groups allow setting QoS rate limits that apply to all clients in that group.
"""

import logging
import json
from typing import Dict, Any, Optional

from src.runtime import server, config
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)


def _get_usergroup_manager():
    """Lazy import to avoid circular dependency."""
    from src.runtime import usergroup_manager
    return usergroup_manager


@server.tool(
    name="unifi_list_usergroups",
    description="List all user groups on the UniFi controller with their bandwidth limits.",
)
async def list_usergroups() -> Dict[str, Any]:
    """Lists all user groups configured for the current UniFi site.

    User groups define bandwidth limits (QoS) that apply to all clients assigned
    to that group. Every site has at least a "Default" group.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - site (str): The identifier of the UniFi site queried.
        - count (int): The number of user groups found.
        - usergroups (List[Dict]): A list of user groups with:
            - id (str): The unique identifier (_id) of the group.
            - name (str): The name of the user group.
            - qos_rate_max_down (int): Download limit in Kbps (-1 = unlimited).
            - qos_rate_max_up (int): Upload limit in Kbps (-1 = unlimited).
            - is_default (bool): Whether this is the default group.
        - error (str, optional): An error message if the operation failed.

    Example response:
    {
        "success": True,
        "site": "default",
        "count": 2,
        "usergroups": [
            {
                "id": "60d4e5f6a7b8c9d0e1f2a3b4",
                "name": "Default",
                "qos_rate_max_down": -1,
                "qos_rate_max_up": -1,
                "is_default": true
            },
            {
                "id": "60d4e5f6a7b8c9d0e1f2a3b5",
                "name": "Limited Guests",
                "qos_rate_max_down": 10000,
                "qos_rate_max_up": 2000,
                "is_default": false
            }
        ]
    }
    """
    if not parse_permission(config.permissions, "usergroup", "read"):
        logger.warning("Permission denied for listing user groups.")
        return {"success": False, "error": "Permission denied to list user groups."}

    try:
        usergroup_manager = _get_usergroup_manager()
        groups = await usergroup_manager.get_usergroups()

        formatted_groups = []
        for g in groups:
            formatted_groups.append({
                "id": g.get("_id"),
                "name": g.get("name"),
                "qos_rate_max_down": g.get("qos_rate_max_down", -1),
                "qos_rate_max_up": g.get("qos_rate_max_up", -1),
                "is_default": g.get("attr_no_delete", False),
            })

        return {
            "success": True,
            "site": usergroup_manager._connection.site,
            "count": len(formatted_groups),
            "usergroups": formatted_groups,
        }
    except Exception as e:
        logger.error(f"Error listing user groups: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_get_usergroup_details",
    description="Get details for a specific user group by ID.",
)
async def get_usergroup_details(group_id: str) -> Dict[str, Any]:
    """Gets the detailed information of a specific user group by its ID.

    Args:
        group_id (str): The unique identifier (_id) of the user group.

    Returns:
        A dictionary containing:
        - success (bool): Indicates if the operation was successful.
        - site (str): The identifier of the UniFi site queried.
        - group_id (str): The ID of the group requested.
        - details (Dict[str, Any]): Full user group details from the controller.
        - error (str, optional): An error message if the operation failed.
    """
    if not parse_permission(config.permissions, "usergroup", "read"):
        logger.warning(f"Permission denied for getting user group details ({group_id}).")
        return {"success": False, "error": "Permission denied to get user group details."}

    try:
        if not group_id:
            return {"success": False, "error": "group_id is required"}

        usergroup_manager = _get_usergroup_manager()
        group = await usergroup_manager.get_usergroup_details(group_id)

        if group:
            return {
                "success": True,
                "site": usergroup_manager._connection.site,
                "group_id": group_id,
                "details": json.loads(json.dumps(group, default=str)),
            }
        else:
            return {
                "success": False,
                "error": f"User group with ID '{group_id}' not found.",
            }
    except Exception as e:
        logger.error(f"Error getting user group {group_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_create_usergroup",
    description=(
        "Create a new user group with optional bandwidth limits. "
        "Requires confirmation."
    ),
    permission_category="usergroups",
    permission_action="create",
)
async def create_usergroup(
    name: str,
    qos_rate_max_down: Optional[int] = None,
    qos_rate_max_up: Optional[int] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Creates a new user group with optional bandwidth limits.

    User groups allow you to apply bandwidth limits to multiple clients at once.
    Assign clients to the group to enforce the limits.

    Args:
        name (str): Name of the user group (must be unique).
        qos_rate_max_down (int, optional): Download rate limit in Kbps.
            Use -1 for unlimited. If not specified, defaults to unlimited.
        qos_rate_max_up (int, optional): Upload rate limit in Kbps.
            Use -1 for unlimited. If not specified, defaults to unlimited.
        confirm (bool): Must be True to execute. Defaults to False.

    Returns:
        A dictionary containing:
        - success (bool): Whether the operation succeeded.
        - site (str): The UniFi site.
        - group_id (str): ID of the created group.
        - details (Dict): The created group details.
        - error (str, optional): Error message if failed.

    Example:
        Create a group with 10 Mbps down / 2 Mbps up limit:
        {
            "name": "Limited Guests",
            "qos_rate_max_down": 10000,
            "qos_rate_max_up": 2000,
            "confirm": true
        }
    """
    if not parse_permission(config.permissions, "usergroup", "create"):
        logger.warning("Permission denied for creating user group.")
        return {"success": False, "error": "Permission denied to create user group."}

    if not confirm:
        return {
            "success": False,
            "error": "Confirmation required. Set 'confirm' to true.",
            "preview": {
                "name": name,
                "qos_rate_max_down": qos_rate_max_down,
                "qos_rate_max_up": qos_rate_max_up,
            },
        }

    if not name or not name.strip():
        return {"success": False, "error": "name is required and cannot be empty"}

    try:
        usergroup_manager = _get_usergroup_manager()

        # Check if name already exists
        existing = await usergroup_manager.get_usergroup_by_name(name)
        if existing:
            return {
                "success": False,
                "error": f"User group with name '{name}' already exists.",
            }

        logger.info(f"Creating user group '{name}'")

        created_group = await usergroup_manager.create_usergroup(
            name=name,
            qos_rate_max_down=qos_rate_max_down,
            qos_rate_max_up=qos_rate_max_up,
        )

        if created_group:
            return {
                "success": True,
                "site": usergroup_manager._connection.site,
                "message": f"User group '{name}' created successfully.",
                "group_id": created_group.get("_id"),
                "details": json.loads(json.dumps(created_group, default=str)),
            }
        else:
            return {
                "success": False,
                "error": "Failed to create user group. Check server logs.",
            }

    except Exception as e:
        logger.error(f"Error creating user group '{name}': {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_update_usergroup",
    description="Update an existing user group's name or bandwidth limits. Requires confirmation.",
    permission_category="usergroups",
    permission_action="update",
)
async def update_usergroup(
    group_id: str,
    name: Optional[str] = None,
    qos_rate_max_down: Optional[int] = None,
    qos_rate_max_up: Optional[int] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Updates an existing user group's settings.

    Only provide the fields you want to change. Omitted fields remain unchanged.

    Args:
        group_id (str): The unique identifier (_id) of the user group to update.
        name (str, optional): New name for the group.
        qos_rate_max_down (int, optional): New download rate limit in Kbps (-1 = unlimited).
        qos_rate_max_up (int, optional): New upload rate limit in Kbps (-1 = unlimited).
        confirm (bool): Must be True to execute. Defaults to False.

    Returns:
        A dictionary containing:
        - success (bool): Whether the operation succeeded.
        - group_id (str): The ID of the updated group.
        - message (str): Confirmation message.
        - details (Dict): Updated group details.
        - error (str, optional): Error message if failed.
    """
    if not parse_permission(config.permissions, "usergroup", "update"):
        logger.warning(f"Permission denied for updating user group ({group_id}).")
        return {"success": False, "error": "Permission denied to update user group."}

    if not group_id:
        return {"success": False, "error": "group_id is required"}

    # Check if any update field is provided
    if name is None and qos_rate_max_down is None and qos_rate_max_up is None:
        return {"success": False, "error": "At least one field to update must be provided."}

    usergroup_manager = _get_usergroup_manager()

    if not confirm:
        # Fetch current state for preview
        group = await usergroup_manager.get_usergroup_details(group_id)
        if not group:
            return {
                "success": False,
                "error": f"User group with ID '{group_id}' not found.",
            }
        return {
            "success": False,
            "error": "Confirmation required. Set 'confirm' to true.",
            "preview": {
                "group_id": group_id,
                "current_name": group.get("name"),
                "new_name": name,
                "current_down": group.get("qos_rate_max_down"),
                "new_down": qos_rate_max_down,
                "current_up": group.get("qos_rate_max_up"),
                "new_up": qos_rate_max_up,
            },
        }

    try:
        logger.info(f"Updating user group {group_id}")

        success = await usergroup_manager.update_usergroup(
            group_id=group_id,
            name=name,
            qos_rate_max_down=qos_rate_max_down,
            qos_rate_max_up=qos_rate_max_up,
        )

        if success:
            # Fetch updated group
            updated_group = await usergroup_manager.get_usergroup_details(group_id)
            return {
                "success": True,
                "group_id": group_id,
                "message": f"User group '{group_id}' updated successfully.",
                "details": json.loads(json.dumps(updated_group, default=str)),
            }
        else:
            return {
                "success": False,
                "error": f"Failed to update user group {group_id}. Check server logs.",
            }

    except Exception as e:
        logger.error(f"Error updating user group {group_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
