"""Policy tools for UniFi Access MCP server.

Provides tools for listing and inspecting access policies and schedules.
"""

import logging
from typing import Any, Dict

from mcp.types import ToolAnnotations

from unifi_access_mcp.runtime import policy_manager, server

logger = logging.getLogger(__name__)


@server.tool(
    name="access_list_policies",
    description=(
        "Lists all access policies configured on the Access controller. "
        "Shows policy name, assigned doors, schedules, and user groups."
    ),
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_list_policies() -> Dict[str, Any]:
    """List all access policies."""
    logger.info("access_list_policies tool called")
    try:
        policies = await policy_manager.list_policies()
        return {"success": True, "data": {"policies": policies, "count": len(policies)}}
    except NotImplementedError:
        return {"success": False, "error": "Policy listing not yet implemented"}
    except Exception as e:
        logger.error("Error listing policies: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to list policies: {e}"}


@server.tool(
    name="access_get_policy",
    description="Returns detailed information for a single access policy.",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_get_policy(policy_id: str) -> Dict[str, Any]:
    """Get detailed policy information by ID."""
    logger.info("access_get_policy tool called for %s", policy_id)
    try:
        detail = await policy_manager.get_policy(policy_id)
        return {"success": True, "data": detail}
    except NotImplementedError:
        return {"success": False, "error": "Policy detail not yet implemented"}
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error("Error getting policy %s: %s", policy_id, e, exc_info=True)
        return {"success": False, "error": f"Failed to get policy: {e}"}


@server.tool(
    name="access_list_schedules",
    description="Lists all access schedules configured on the Access controller.",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def access_list_schedules() -> Dict[str, Any]:
    """List all access schedules."""
    logger.info("access_list_schedules tool called")
    try:
        schedules = await policy_manager.list_schedules()
        return {"success": True, "data": {"schedules": schedules, "count": len(schedules)}}
    except NotImplementedError:
        return {"success": False, "error": "Schedule listing not yet implemented"}
    except Exception as e:
        logger.error("Error listing schedules: %s", e, exc_info=True)
        return {"success": False, "error": f"Failed to list schedules: {e}"}


logger.info("Policy tools registered: access_list_policies, access_get_policy, access_list_schedules")
