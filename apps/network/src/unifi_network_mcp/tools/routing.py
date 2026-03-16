"""
UniFi Network MCP static routing tools.

This module provides MCP tools to manage static routes on a UniFi Network Controller.
"""

import logging
import re
from typing import Any, Dict, Optional

from src.runtime import config, server
from src.utils.confirmation import create_preview, should_auto_confirm, update_preview
from src.utils.permissions import parse_permission

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependencies
_routing_manager = None


def _get_routing_manager():
    """Lazy-load the routing manager to avoid circular imports."""
    global _routing_manager
    if _routing_manager is None:
        from src.managers.routing_manager import RoutingManager
        from src.runtime import get_connection_manager

        _routing_manager = RoutingManager(get_connection_manager())
    return _routing_manager


def _validate_cidr(network: str) -> bool:
    """Validate a CIDR network notation."""
    pattern = r"^(\d{1,3}\.){3}\d{1,3}/\d{1,2}$"
    if not re.match(pattern, network):
        return False
    parts = network.split("/")
    ip_parts = parts[0].split(".")
    prefix = int(parts[1])
    return all(0 <= int(p) <= 255 for p in ip_parts) and 0 <= prefix <= 32


def _validate_ip(ip: str) -> bool:
    """Validate an IP address."""
    pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    if not re.match(pattern, ip):
        return False
    return all(0 <= int(p) <= 255 for p in ip.split("."))


@server.tool(
    name="unifi_list_routes",
    description="""List all user-defined static routes for the current site.

Returns route names, destination networks, next-hop addresses, and status.
These are manually configured routes, not dynamic or system routes.""",
)
async def list_routes() -> Dict[str, Any]:
    """List all user-defined static routes."""
    try:
        routing_manager = _get_routing_manager()
        routes = await routing_manager.get_routes()

        # Format routes for readability
        formatted_routes = []
        for r in routes:
            formatted = {
                "_id": r.get("_id"),
                "name": r.get("name"),
                "network": r.get("static-route_network"),
                "nexthop": r.get("static-route_nexthop"),
                "distance": r.get("static-route_distance", 1),
                "enabled": r.get("enabled", True),
                "type": r.get("type", "nexthop-route"),
            }
            formatted_routes.append(formatted)

        return {
            "success": True,
            "site": routing_manager._connection.site,
            "count": len(formatted_routes),
            "routes": formatted_routes,
        }
    except Exception as e:
        logger.error(f"Error listing routes: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_list_active_routes",
    description="""List all active routes from the device routing table.

Includes both user-defined and system routes currently in effect.
This shows the actual routing table state on the gateway device.

Note: This endpoint may not be available on all controller versions.
Returns empty list if unavailable.""",
)
async def list_active_routes() -> Dict[str, Any]:
    """List all active routes from the routing table."""
    try:
        routing_manager = _get_routing_manager()
        routes = await routing_manager.get_active_routes()

        return {
            "success": True,
            "site": routing_manager._connection.site,
            "count": len(routes),
            "active_routes": routes,
        }
    except Exception as e:
        logger.error(f"Error listing active routes: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_get_route_details",
    description="Get detailed information about a specific static route by its ID",
)
async def get_route_details(route_id: str) -> Dict[str, Any]:
    """Get details for a specific route."""
    try:
        routing_manager = _get_routing_manager()
        route = await routing_manager.get_route_details(route_id)

        if route:
            return {
                "success": True,
                "site": routing_manager._connection.site,
                "route": route,
            }
        return {
            "success": False,
            "error": f"Route not found with ID: {route_id}",
        }
    except Exception as e:
        logger.error(f"Error getting route details for {route_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_create_route",
    description="""Create a new static route for advanced routing configuration.

Specify destination network in CIDR format (e.g., "10.0.0.0/24") and
next-hop IP address (e.g., "192.168.1.1").""",
    permission_category="routes",
    permission_action="create",
)
async def create_route(
    name: str,
    network: str,
    nexthop: str,
    distance: int = 1,
    enabled: bool = True,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Create a new static route."""
    if not parse_permission(config.permissions, "route", "create"):
        logger.warning("Permission denied for creating routes.")
        return {"success": False, "error": "Permission denied to create routes."}

    if not name or not name.strip():
        return {"success": False, "error": "Name is required."}

    if not _validate_cidr(network):
        return {
            "success": False,
            "error": f"Invalid network format: {network}. Use CIDR notation (e.g., 10.0.0.0/24).",
        }

    if not _validate_ip(nexthop):
        return {
            "success": False,
            "error": f"Invalid nexthop IP: {nexthop}. Use valid IP address.",
        }

    if distance < 1 or distance > 255:
        return {"success": False, "error": "Distance must be between 1 and 255."}

    if not confirm and not should_auto_confirm():
        return create_preview(
            resource_type="static_route",
            resource_data={
                "name": name.strip(),
                "network": network,
                "nexthop": nexthop,
                "distance": distance,
                "enabled": enabled,
            },
            resource_name=name.strip(),
        )

    try:
        routing_manager = _get_routing_manager()
        route = await routing_manager.create_route(
            name=name.strip(),
            static_route_network=network,
            static_route_nexthop=nexthop,
            static_route_distance=distance,
            enabled=enabled,
        )

        if route:
            return {
                "success": True,
                "message": f"Route '{name}' created successfully.",
                "site": routing_manager._connection.site,
                "route": route,
            }
        return {"success": False, "error": "Failed to create route."}
    except Exception as e:
        logger.error(f"Error creating route: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@server.tool(
    name="unifi_update_route",
    description="""Update an existing static route's properties.

Can modify name, destination network, next-hop, distance, or enabled status.""",
    permission_category="routes",
    permission_action="update",
)
async def update_route(
    route_id: str,
    name: Optional[str] = None,
    network: Optional[str] = None,
    nexthop: Optional[str] = None,
    distance: Optional[int] = None,
    enabled: Optional[bool] = None,
    confirm: bool = False,
) -> Dict[str, Any]:
    """Update an existing static route."""
    if not parse_permission(config.permissions, "route", "update"):
        logger.warning(f"Permission denied for updating route ({route_id}).")
        return {"success": False, "error": "Permission denied to update routes."}

    # Validate that at least one update is provided
    if all(v is None for v in [name, network, nexthop, distance, enabled]):
        return {
            "success": False,
            "error": "At least one field must be provided.",
        }

    # Validate formats if provided
    if network is not None and not _validate_cidr(network):
        return {
            "success": False,
            "error": f"Invalid network format: {network}. Use CIDR notation.",
        }

    if nexthop is not None and not _validate_ip(nexthop):
        return {
            "success": False,
            "error": f"Invalid nexthop IP: {nexthop}.",
        }

    if distance is not None and (distance < 1 or distance > 255):
        return {"success": False, "error": "Distance must be between 1 and 255."}

    try:
        routing_manager = _get_routing_manager()

        # Fetch current route state for preview
        current_route = await routing_manager.get_route_details(route_id)
        if not current_route:
            return {
                "success": False,
                "error": f"Route not found with ID: {route_id}",
            }

        if not confirm and not should_auto_confirm():
            # Build current state from the route
            current_state = {
                "name": current_route.get("name"),
                "network": current_route.get("static-route_network"),
                "nexthop": current_route.get("static-route_nexthop"),
                "distance": current_route.get("static-route_distance", 1),
                "enabled": current_route.get("enabled", True),
            }

            # Build updates dict with only provided values
            updates = {
                k: v
                for k, v in {
                    "name": name.strip() if name else None,
                    "network": network,
                    "nexthop": nexthop,
                    "distance": distance,
                    "enabled": enabled,
                }.items()
                if v is not None
            }

            return update_preview(
                resource_type="static_route",
                resource_id=route_id,
                resource_name=current_route.get("name"),
                current_state=current_state,
                updates=updates,
            )

        success = await routing_manager.update_route(
            route_id=route_id,
            name=name.strip() if name else None,
            static_route_network=network,
            static_route_nexthop=nexthop,
            static_route_distance=distance,
            enabled=enabled,
        )

        if success:
            return {
                "success": True,
                "message": f"Route {route_id} updated successfully.",
                "updates": {
                    k: v
                    for k, v in {
                        "name": name,
                        "network": network,
                        "nexthop": nexthop,
                        "distance": distance,
                        "enabled": enabled,
                    }.items()
                    if v is not None
                },
            }
        return {"success": False, "error": f"Failed to update route {route_id}."}
    except Exception as e:
        logger.error(f"Error updating route {route_id}: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
