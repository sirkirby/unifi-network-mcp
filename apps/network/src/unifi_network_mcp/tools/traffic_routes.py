"""
UniFi Network MCP traffic route tools.

This module provides MCP tools to manage traffic routes (policy-based routing)
on a UniFi Network Controller using the V2 API.
"""

import logging
from typing import Annotated, Any, Dict, Optional

from mcp.types import ToolAnnotations
from pydantic import Field

from unifi_mcp_shared.confirmation import should_auto_confirm, toggle_preview, update_preview
from unifi_network_mcp.categories import parse_permission
from unifi_network_mcp.runtime import config, server

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependencies
_traffic_route_manager = None


def _get_traffic_route_manager():
    """Lazy-load the traffic route manager to avoid circular imports."""
    global _traffic_route_manager
    if _traffic_route_manager is None:
        from unifi_network_mcp.managers.traffic_route_manager import TrafficRouteManager
        from unifi_network_mcp.runtime import get_connection_manager

        _traffic_route_manager = TrafficRouteManager(get_connection_manager())
    return _traffic_route_manager


@server.tool(
    name="unifi_list_traffic_routes",
    description="""List all traffic routes (policy-based routing rules) for the current site.

Traffic routes define how specific traffic is routed based on domains,
IP addresses, regions, or target devices. Often used for VPN routing.""",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def list_traffic_routes() -> Dict[str, Any]:
    """List all traffic routes."""
    try:
        traffic_route_manager = _get_traffic_route_manager()
        routes = await traffic_route_manager.get_traffic_routes()

        # Format routes for readability
        formatted_routes = []
        for r in routes:
            formatted = {
                "_id": r.get("_id"),
                "description": r.get("description"),
                "enabled": r.get("enabled", True),
                "network_id": r.get("network_id"),
                "next_hop": r.get("next_hop"),
                "matching_target": r.get("matching_target"),
                "kill_switch_enabled": r.get("kill_switch_enabled", False),
                "domains": len(r.get("domains", [])),
                "ip_addresses": len(r.get("ip_addresses", [])),
                "ip_ranges": len(r.get("ip_ranges", [])),
                "regions": len(r.get("regions", [])),
                "target_devices": len(r.get("target_devices", [])),
            }
            formatted_routes.append(formatted)

        return {
            "success": True,
            "site": traffic_route_manager._connection.site,
            "count": len(formatted_routes),
            "traffic_routes": formatted_routes,
        }
    except Exception as e:
        logger.error(f"Error listing traffic routes: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to list traffic routes: {e}"}


@server.tool(
    name="unifi_get_traffic_route_details",
    description="Get detailed information for a specific traffic route by ID.",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_traffic_route_details(
    route_id: Annotated[
        str,
        Field(description="Unique identifier (_id) of the traffic route (from unifi_list_traffic_routes)"),
    ],
) -> Dict[str, Any]:
    """Get details for a specific traffic route."""
    try:
        traffic_route_manager = _get_traffic_route_manager()
        route = await traffic_route_manager.get_traffic_route_details(route_id)

        if route:
            return {
                "success": True,
                "site": traffic_route_manager._connection.site,
                "route_id": route_id,
                "details": route,
            }
        else:
            return {"success": False, "error": f"Traffic route '{route_id}' not found."}
    except Exception as e:
        logger.error(f"Error getting traffic route details: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to get traffic route details: {e}"}


@server.tool(
    name="unifi_update_traffic_route",
    description="""Update a traffic route's settings.

Can update:
- enabled: Enable or disable the traffic route
- kill_switch_enabled: Enable/disable the kill switch (blocks traffic if VPN is down)

At least one parameter must be provided.""",
    permission_category="traffic_routes",
    permission_action="update",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False),
)
async def update_traffic_route(
    route_id: Annotated[
        str,
        Field(description="Unique identifier (_id) of the traffic route to update (from unifi_list_traffic_routes)"),
    ],
    enabled: Annotated[Optional[bool], Field(description="Enable (true) or disable (false) the traffic route")] = None,
    kill_switch_enabled: Annotated[
        Optional[bool],
        Field(
            description="Enable (true) or disable (false) the kill switch, which blocks traffic if the VPN goes down"
        ),
    ] = None,
    confirm: Annotated[
        bool,
        Field(description="When true, applies the update. When false (default), returns a preview of the changes"),
    ] = False,
) -> Dict[str, Any]:
    """Update a traffic route's settings."""
    if enabled is None and kill_switch_enabled is None:
        return {
            "success": False,
            "error": "At least one of 'enabled' or 'kill_switch_enabled' must be provided.",
        }

    if not parse_permission(config.permissions, "traffic_route", "update"):
        logger.warning(f"Permission denied for updating traffic route ({route_id}).")
        return {
            "success": False,
            "error": "Permission denied to update traffic route.",
        }

    try:
        traffic_route_manager = _get_traffic_route_manager()

        # Fetch current state for preview
        current = await traffic_route_manager.get_traffic_route_details(route_id)
        if not current:
            return {"success": False, "error": f"Traffic route '{route_id}' not found."}

        route_name = current.get("description", route_id)

        # Build update dict for preview and execution
        updates: Dict[str, Any] = {}
        if enabled is not None:
            updates["enabled"] = enabled
        if kill_switch_enabled is not None:
            updates["kill_switch_enabled"] = kill_switch_enabled

        # Return preview when confirm=false
        if not confirm and not should_auto_confirm():
            return update_preview(
                resource_type="traffic_route",
                resource_id=route_id,
                resource_name=route_name,
                current_state={
                    "enabled": current.get("enabled"),
                    "kill_switch_enabled": current.get("kill_switch_enabled"),
                    "network_id": current.get("network_id"),
                },
                updates=updates,
            )

        success = await traffic_route_manager.update_traffic_route(route_id, **updates)

        if success:
            route = await traffic_route_manager.get_traffic_route_details(route_id)
            desc = route.get("description", route_id) if route else route_id

            changes = []
            if enabled is not None:
                changes.append(f"enabled={'on' if enabled else 'off'}")
            if kill_switch_enabled is not None:
                changes.append(f"kill_switch={'on' if kill_switch_enabled else 'off'}")

            return {
                "success": True,
                "message": f"Traffic route '{desc}' updated: {', '.join(changes)}.",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to update traffic route {route_id}.",
            }
    except Exception as e:
        logger.error(f"Error updating traffic route: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to update traffic route: {e}"}


@server.tool(
    name="unifi_toggle_traffic_route",
    description="Toggle a traffic route on/off by ID.",
    permission_category="traffic_routes",
    permission_action="update",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False),
)
async def toggle_traffic_route(
    route_id: Annotated[
        str,
        Field(description="Unique identifier (_id) of the traffic route to toggle (from unifi_list_traffic_routes)"),
    ],
    confirm: Annotated[
        bool,
        Field(description="When true, executes the toggle. When false (default), returns a preview of the changes"),
    ] = False,
) -> Dict[str, Any]:
    """Toggle a traffic route's enabled state."""
    if not parse_permission(config.permissions, "traffic_route", "update"):
        logger.warning(f"Permission denied for toggling traffic route ({route_id}).")
        return {
            "success": False,
            "error": "Permission denied to toggle traffic route.",
        }

    try:
        traffic_route_manager = _get_traffic_route_manager()

        # Get current state for preview/message
        current = await traffic_route_manager.get_traffic_route_details(route_id)
        if not current:
            return {"success": False, "error": f"Traffic route '{route_id}' not found."}

        current_enabled = current.get("enabled", True)
        route_name = current.get("description", route_id)

        # Return preview when confirm=false
        if not confirm and not should_auto_confirm():
            return toggle_preview(
                resource_type="traffic_route",
                resource_id=route_id,
                resource_name=route_name,
                current_enabled=current_enabled,
                additional_info={
                    "network_id": current.get("network_id"),
                    "kill_switch_enabled": current.get("kill_switch_enabled"),
                },
            )

        success = await traffic_route_manager.toggle_traffic_route(route_id)

        if success:
            new_state = "enabled" if not current_enabled else "disabled"
            return {
                "success": True,
                "message": f"Traffic route '{route_name}' toggled to {new_state}.",
            }
        else:
            return {
                "success": False,
                "error": f"Failed to toggle traffic route {route_id}.",
            }
    except Exception as e:
        logger.error(f"Error toggling traffic route: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to toggle traffic route: {e}"}
