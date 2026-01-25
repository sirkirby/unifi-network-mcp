# ruff: noqa: E402
from __future__ import annotations

"""Shared runtime objects for the UniFi‑Network MCP server.

This module is the *single* source of truth for global singletons such as the
FastMCP server instance, loaded configuration, and all manager helpers.

Downstream code (tool modules, tests, etc.) should import these via::

    from src.runtime import server, config, device_manager

Lazy factories (`get_*`) are provided so unit tests can substitute fakes by
monkey‑patching before the first call.

IMPORTANT: The server's `tool` decorator is wrapped here (not in main.py) to
ensure that tool modules can be imported directly (for testing, etc.) without
errors from unrecognized decorator kwargs like `permission_category`.
"""

import os
from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from src.bootstrap import load_config, logger
from src.managers.client_manager import ClientManager
from src.managers.connection_manager import ConnectionManager
from src.managers.device_manager import DeviceManager
from src.managers.event_manager import EventManager
from src.managers.firewall_manager import FirewallManager
from src.managers.hotspot_manager import HotspotManager
from src.managers.network_manager import NetworkManager
from src.managers.qos_manager import QosManager
from src.managers.routing_manager import RoutingManager
from src.managers.stats_manager import StatsManager
from src.managers.system_manager import SystemManager
from src.managers.traffic_route_manager import TrafficRouteManager
from src.managers.usergroup_manager import UsergroupManager
from src.managers.vpn_manager import VpnManager
from src.tool_index import TOOL_REGISTRY

# ---------------------------------------------------------------------------
# Core singletons
# ---------------------------------------------------------------------------


@lru_cache
def get_config():
    """Load and cache configuration."""
    return load_config()


def _create_permissioned_tool_wrapper(original_tool_decorator):
    """Wrap the FastMCP tool decorator to handle permission kwargs.

    This wrapper strips `permission_category` and `permission_action` kwargs
    before passing to the original FastMCP decorator. This allows tool modules
    to be imported directly (for testing, etc.) without errors.

    The actual permission checking is done in main.py's permissioned_tool,
    which replaces this wrapper at startup. This wrapper just ensures imports
    don't fail when tools have permission kwargs.
    """
    def wrapper(*args, **kwargs):
        # Strip permission-related kwargs that FastMCP doesn't understand
        kwargs.pop("permission_category", None)
        kwargs.pop("permission_action", None)
        return original_tool_decorator(*args, **kwargs)
    return wrapper


@lru_cache
def get_server() -> FastMCP:
    """Create the FastMCP server instance exactly once."""
    # Parse allowed hosts from environment variable for reverse proxy support
    # Default to localhost only for backwards compatibility
    allowed_hosts_str = os.getenv("UNIFI_MCP_ALLOWED_HOSTS", "localhost,127.0.0.1")
    allowed_hosts = [h.strip() for h in allowed_hosts_str.split(",") if h.strip()]

    # Configure transport security settings
    transport_security = TransportSecuritySettings(allowed_hosts=allowed_hosts)

    logger.debug(f"Configuring FastMCP with allowed_hosts: {allowed_hosts}")

    server = FastMCP(
        name="unifi-network-mcp",
        debug=True,
        transport_security=transport_security,
    )

    # Wrap the tool decorator to handle permission kwargs gracefully.
    # This ensures tool modules can be imported directly without errors.
    # main.py will replace this with the full permissioned_tool implementation.
    server._original_tool = server.tool
    server.tool = _create_permissioned_tool_wrapper(server.tool)

    return server


# ---------------------------------------------------------------------------
# Manager factories ---------------------------------------------------------
# ---------------------------------------------------------------------------


def _unifi_settings() -> Any:
    cfg = get_config().unifi
    return cfg


@lru_cache
def get_connection_manager() -> ConnectionManager:
    cfg = _unifi_settings()
    return ConnectionManager(
        host=cfg.host,
        username=cfg.username,
        password=cfg.password,
        port=cfg.port,
        site=cfg.site,
        verify_ssl=cfg.verify_ssl,
    )


@lru_cache
def get_client_manager() -> ClientManager:
    return ClientManager(get_connection_manager())


@lru_cache
def get_device_manager() -> DeviceManager:
    return DeviceManager(get_connection_manager())


@lru_cache
def get_stats_manager() -> StatsManager:
    return StatsManager(get_connection_manager(), get_client_manager())


@lru_cache
def get_qos_manager() -> QosManager:
    return QosManager(get_connection_manager())


@lru_cache
def get_vpn_manager() -> VpnManager:
    return VpnManager(get_connection_manager())


@lru_cache
def get_network_manager() -> NetworkManager:
    return NetworkManager(get_connection_manager())


@lru_cache
def get_system_manager() -> SystemManager:
    return SystemManager(get_connection_manager())


@lru_cache
def get_firewall_manager() -> FirewallManager:
    return FirewallManager(get_connection_manager())


@lru_cache
def get_event_manager() -> EventManager:
    return EventManager(get_connection_manager())


@lru_cache
def get_hotspot_manager() -> HotspotManager:
    return HotspotManager(get_connection_manager())


@lru_cache
def get_usergroup_manager() -> UsergroupManager:
    return UsergroupManager(get_connection_manager())


@lru_cache
def get_routing_manager() -> RoutingManager:
    return RoutingManager(get_connection_manager())


@lru_cache
def get_traffic_route_manager() -> TrafficRouteManager:
    return TrafficRouteManager(get_connection_manager())


@lru_cache
def get_tool_registry() -> dict[str, Any]:
    """Return the global tool registry for runtime access."""
    return TOOL_REGISTRY


# ---------------------------------------------------------------------------
# Shorthand aliases (import‑time singletons) --------------------------------
# ---------------------------------------------------------------------------

# These provide the convenient attribute style while still being created lazily
# the first time the corresponding factory is called.

config = get_config()
server = get_server()
connection_manager = get_connection_manager()
client_manager = get_client_manager()
device_manager = get_device_manager()
stats_manager = get_stats_manager()
qos_manager = get_qos_manager()
vpn_manager = get_vpn_manager()
network_manager = get_network_manager()
system_manager = get_system_manager()
firewall_manager = get_firewall_manager()
event_manager = get_event_manager()
hotspot_manager = get_hotspot_manager()
usergroup_manager = get_usergroup_manager()
routing_manager = get_routing_manager()
traffic_route_manager = get_traffic_route_manager()
tool_registry = get_tool_registry()

logger.debug("runtime.py: shared singletons initialised")
