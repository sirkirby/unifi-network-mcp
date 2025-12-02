"""Lazy tool loader for on-demand tool registration.

This module implements true lazy loading of tools, registering them only
when first called by an LLM. This dramatically reduces initial context usage.
"""

import importlib
import logging
from functools import wraps
from typing import Any, Callable, Dict, Set

logger = logging.getLogger("unifi-network-mcp")

# Tool module mapping: tool_name -> module_path
TOOL_MODULE_MAP: Dict[str, str] = {
    # Client tools
    "unifi_list_clients": "src.tools.clients",
    "unifi_get_client_details": "src.tools.clients",
    "unifi_list_blocked_clients": "src.tools.clients",
    "unifi_block_client": "src.tools.clients",
    "unifi_unblock_client": "src.tools.clients",
    "unifi_rename_client": "src.tools.clients",
    "unifi_force_reconnect_client": "src.tools.clients",
    "unifi_authorize_guest": "src.tools.clients",
    "unifi_unauthorize_guest": "src.tools.clients",
    "unifi_set_client_ip_settings": "src.tools.clients",
    # Device tools
    "unifi_list_devices": "src.tools.devices",
    "unifi_get_device_details": "src.tools.devices",
    "unifi_reboot_device": "src.tools.devices",
    "unifi_locate_device": "src.tools.devices",
    "unifi_adopt_device": "src.tools.devices",
    "unifi_upgrade_device": "src.tools.devices",
    "unifi_set_device_name": "src.tools.devices",
    "unifi_power_cycle_port": "src.tools.devices",
    "unifi_set_port_profile": "src.tools.devices",
    # Network tools
    "unifi_list_networks": "src.tools.networks",
    "unifi_get_network_details": "src.tools.networks",
    "unifi_create_network": "src.tools.networks",
    "unifi_update_network": "src.tools.networks",
    "unifi_delete_network": "src.tools.networks",
    # Firewall tools
    "unifi_list_firewall_rules": "src.tools.firewall",
    "unifi_get_firewall_rule": "src.tools.firewall",
    "unifi_create_firewall_rule": "src.tools.firewall",
    "unifi_update_firewall_rule": "src.tools.firewall",
    "unifi_delete_firewall_rule": "src.tools.firewall",
    "unifi_enable_firewall_rule": "src.tools.firewall",
    "unifi_disable_firewall_rule": "src.tools.firewall",
    "unifi_list_firewall_groups": "src.tools.firewall",
    "unifi_create_firewall_group": "src.tools.firewall",
    "unifi_update_firewall_group": "src.tools.firewall",
    "unifi_delete_firewall_group": "src.tools.firewall",
    # VPN tools
    "unifi_list_vpn_servers": "src.tools.vpn",
    "unifi_get_vpn_server_details": "src.tools.vpn",
    "unifi_update_vpn_server_state": "src.tools.vpn",
    "unifi_list_vpn_clients": "src.tools.vpn",
    "unifi_get_vpn_client_details": "src.tools.vpn",
    "unifi_update_vpn_client_state": "src.tools.vpn",
    # QoS tools
    "unifi_list_qos_rules": "src.tools.qos",
    "unifi_create_qos_rule": "src.tools.qos",
    "unifi_update_qos_rule": "src.tools.qos",
    "unifi_delete_qos_rule": "src.tools.qos",
    # Statistics tools
    "unifi_get_client_stats": "src.tools.stats",
    "unifi_get_device_stats": "src.tools.stats",
    "unifi_get_network_stats": "src.tools.stats",
    "unifi_get_wireless_stats": "src.tools.stats",
    "unifi_get_system_stats": "src.tools.stats",
    # System tools
    "unifi_get_system_info": "src.tools.system",
    "unifi_get_network_health": "src.tools.system",
    "unifi_get_site_settings": "src.tools.system",
    # Event tools
    "unifi_list_events": "src.tools.events",
    "unifi_list_alarms": "src.tools.events",
    "unifi_get_event_types": "src.tools.events",
    "unifi_archive_alarm": "src.tools.events",
    "unifi_archive_all_alarms": "src.tools.events",
    # Hotspot/Voucher tools
    "unifi_list_vouchers": "src.tools.hotspot",
    "unifi_get_voucher_details": "src.tools.hotspot",
    "unifi_create_voucher": "src.tools.hotspot",
    "unifi_revoke_voucher": "src.tools.hotspot",
    # User group tools
    "unifi_list_usergroups": "src.tools.usergroups",
    "unifi_get_usergroup_details": "src.tools.usergroups",
    "unifi_create_usergroup": "src.tools.usergroups",
    "unifi_update_usergroup": "src.tools.usergroups",
    # Static Routing tools (V1 API)
    "unifi_list_routes": "src.tools.routing",
    "unifi_list_active_routes": "src.tools.routing",
    "unifi_get_route_details": "src.tools.routing",
    "unifi_create_route": "src.tools.routing",
    "unifi_update_route": "src.tools.routing",
    # Traffic Route tools (V2 API - policy-based routing)
    "unifi_list_traffic_routes": "src.tools.traffic_routes",
    "unifi_get_traffic_route_details": "src.tools.traffic_routes",
    "unifi_update_traffic_route": "src.tools.traffic_routes",
    "unifi_toggle_traffic_route": "src.tools.traffic_routes",
}


class LazyToolLoader:
    """Manages lazy/on-demand tool loading."""

    def __init__(self, server, tool_decorator: Callable):
        """Initialize the lazy tool loader.

        Args:
            server: FastMCP server instance
            tool_decorator: The decorator function to register tools
        """
        self.server = server
        self.tool_decorator = tool_decorator
        self.loaded_modules: Set[str] = set()
        self.loaded_tools: Set[str] = set()
        self._loading = False

        logger.info("Lazy tool loader initialized")

    def is_loaded(self, tool_name: str) -> bool:
        """Check if a tool is already loaded."""
        return tool_name in self.loaded_tools

    async def load_tool(self, tool_name: str) -> bool:
        """Load a tool on-demand.

        Args:
            tool_name: Name of the tool to load

        Returns:
            True if tool was loaded successfully, False otherwise
        """
        # Avoid recursive loading
        if self._loading:
            return False

        if self.is_loaded(tool_name):
            logger.debug(f"Tool '{tool_name}' already loaded")
            return True

        module_path = TOOL_MODULE_MAP.get(tool_name)
        if not module_path:
            logger.warning(f"No module mapping found for tool '{tool_name}'")
            return False

        try:
            self._loading = True
            logger.info(f"🔄 Lazy-loading tool '{tool_name}' from '{module_path}'")

            # Import the module (this will trigger @server.tool decorators)
            if module_path not in self.loaded_modules:
                importlib.import_module(module_path)
                self.loaded_modules.add(module_path)

            # Mark tool as loaded
            self.loaded_tools.add(tool_name)

            logger.info(f"✅ Tool '{tool_name}' loaded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to load tool '{tool_name}': {e}", exc_info=True)
            return False
        finally:
            self._loading = False

    async def intercept_call_tool(self, original_call_tool: Callable, name: str, arguments: dict) -> Any:
        """Intercept tool calls to load tools on-demand.

        Args:
            original_call_tool: Original call_tool method
            name: Tool name
            arguments: Tool arguments

        Returns:
            Result from the tool execution
        """
        # Try to load the tool if not already loaded
        if not self.is_loaded(name) and name in TOOL_MODULE_MAP:
            loaded = await self.load_tool(name)
            if not loaded:
                raise ValueError(f"Failed to load tool '{name}'")

        # Call the original method
        return await original_call_tool(name, arguments)


def setup_lazy_loading(server, tool_decorator: Callable) -> LazyToolLoader:
    """Setup lazy tool loading by intercepting call_tool.

    Args:
        server: FastMCP server instance
        tool_decorator: The decorator function to register tools

    Returns:
        LazyToolLoader instance
    """
    loader = LazyToolLoader(server, tool_decorator)

    # Intercept call_tool to load tools on-demand
    original_call_tool = server.call_tool

    @wraps(original_call_tool)
    async def lazy_call_tool(name: str, arguments: dict):
        return await loader.intercept_call_tool(original_call_tool, name, arguments)

    server.call_tool = lazy_call_tool

    logger.info("✨ Lazy tool loading enabled - tools will be loaded on first use")

    return loader
