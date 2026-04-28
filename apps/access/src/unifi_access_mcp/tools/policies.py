"""Policy tools for UniFi Access MCP server.

Provides tools for listing, inspecting, and updating access policies and schedules.
"""

import logging
from typing import Annotated, Any, Dict

from mcp.types import ToolAnnotations
from pydantic import Field

from unifi_access_mcp.runtime import policy_manager, server
from unifi_core.confirmation import update_preview

logger = logging.getLogger(__name__)


@server.tool(
    name="access_list_policies",
    description=(
        "Lists all access policies configured on the Access controller. "
        "Shows policy name, assigned doors, schedules, and user groups."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    permission_category="policy",
    permission_action="read",
    auth="local_only",
)
async def access_list_policies() -> Dict[str, Any]:
    """List all access policies."""
    logger.info("access_list_policies tool called")
    try:
        policies = await policy_manager.list_policies()
        return {"success": True, "data": {"policies": policies, "count": len(policies)}}
    except Exception as e:
        logger.error("Error listing policies: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to list policies: {e}"}


@server.tool(
    name="access_get_policy",
    description=(
        "Returns detailed information for a single access policy including "
        "assigned doors, schedule, user groups, and configuration."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    permission_category="policy",
    permission_action="read",
    auth="local_only",
)
async def access_get_policy(
    policy_id: Annotated[str, Field(description="Policy UUID (from access_list_policies)")],
) -> Dict[str, Any]:
    """Get detailed policy information by ID."""
    logger.info("access_get_policy tool called for %s", policy_id)
    try:
        detail = await policy_manager.get_policy(policy_id)
        return {"success": True, "data": detail}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("Error getting policy %s: %s", policy_id, e, exc_info=True)
        return {"success": False, "error": f"Failed to get policy: {e}"}


@server.tool(
    name="access_list_schedules",
    description="Lists all access schedules configured on the Access controller.",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    permission_category="schedule",
    permission_action="read",
    auth="local_only",
)
async def access_list_schedules() -> Dict[str, Any]:
    """List all access schedules."""
    logger.info("access_list_schedules tool called")
    try:
        schedules = await policy_manager.list_schedules()
        return {"success": True, "data": {"schedules": schedules, "count": len(schedules)}}
    except Exception as e:
        logger.error("Error listing schedules: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to list schedules: {e}"}


@server.tool(
    name="access_update_policy",
    description=(
        "Update an access policy's configuration. Supported fields include "
        "name, doors, schedule_id, and user groups. "
        "Requires confirm=true to apply. Only available via local proxy session."
    ),
    annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=True, openWorldHint=False),
    permission_category="policy",
    permission_action="update",
    auth="local_only",
)
async def access_update_policy(
    policy_id: Annotated[str, Field(description="Policy UUID (from access_list_policies)")],
    changes: Annotated[
        dict,
        Field(
            description=(
                "Dictionary of fields to update. Supported keys: "
                "name (string - policy display name), "
                "doors (list - door UUIDs to assign), "
                "schedule_id (string - schedule UUID to assign), "
                "user_groups (list - user group UUIDs)."
            )
        ),
    ],
    confirm: Annotated[
        bool,
        Field(description="When true, applies the update. When false (default), returns a preview."),
    ] = False,
) -> Dict[str, Any]:
    """Update a policy with preview/confirm."""
    logger.info("access_update_policy tool called for %s (confirm=%s)", policy_id, confirm)
    try:
        if not changes:
            return {"success": False, "error": "No changes provided. Specify at least one field to update."}

        if confirm:
            result = await policy_manager.apply_update_policy(policy_id, changes)
            return {"success": True, "data": result}

        preview_data = await policy_manager.update_policy(policy_id, changes)
        return update_preview(
            resource_type="access_policy",
            resource_id=policy_id,
            resource_name=preview_data.get("policy_name"),
            current_state=preview_data["current_state"],
            updates=preview_data["proposed_changes"],
        )
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("Error updating policy %s: %s", policy_id, e, exc_info=True)
        return {"success": False, "error": f"Failed to update policy: {e}"}


logger.info(
    "Policy tools registered: access_list_policies, access_get_policy, access_list_schedules, access_update_policy"
)
