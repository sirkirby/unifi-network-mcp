from __future__ import annotations

"""Shared runtime objects for the UniFi‑Network MCP server.

This module is the *single* source of truth for global singletons such as the
FastMCP server instance, loaded configuration, and all manager helpers.

Downstream code (tool modules, tests, etc.) should import these via::

    from src.runtime import server, config, device_manager

Lazy factories (`get_*`) are provided so unit tests can substitute fakes by
monkey‑patching before the first call.
"""

from functools import lru_cache
from typing import Any

from mcp.server.fastmcp import FastMCP

from src.bootstrap import logger, load_config
from src.managers.connection_manager import ConnectionManager
from src.managers.client_manager import ClientManager
from src.managers.device_manager import DeviceManager
from src.managers.stats_manager import StatsManager
from src.managers.qos_manager import QosManager
from src.managers.vpn_manager import VpnManager
from src.managers.network_manager import NetworkManager
from src.managers.system_manager import SystemManager
from src.managers.firewall_manager import FirewallManager

# ---------------------------------------------------------------------------
# Core singletons
# ---------------------------------------------------------------------------


@lru_cache
def get_config():
    """Load and cache configuration."""
    return load_config()


@lru_cache
def get_server() -> FastMCP:
    """Create the FastMCP server instance exactly once."""
    return FastMCP(name="unifi-network-mcp", debug=True)


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

logger.debug("runtime.py: shared singletons initialised") 