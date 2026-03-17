"""VPN management for UniFi Network MCP server.

VPN configurations are stored in the networkconf API endpoint alongside regular
networks. They're identified by the 'purpose' field (vpn-client, vpn-server,
remote-user-vpn) and/or 'vpn_type' field (wireguard-client, openvpn-server, etc).

Note: UniFi is developing a dedicated VPN API but it's not yet complete.
This implementation uses the networkconf endpoint which is the reliable approach.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from aiounifi.models.api import ApiRequest

from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_VPN_CONFIGS = "vpn_configs"
CACHE_PREFIX_NETWORKS = "networks"


def is_vpn_network(network: Dict[str, Any]) -> bool:
    """Check if a network configuration represents a VPN entity.

    Args:
        network: Network configuration dictionary

    Returns:
        True if this is a VPN configuration
    """
    purpose = str(network.get("purpose", "")).lower()
    vpn_type = str(network.get("vpn_type", "")).lower()

    return (
        purpose.startswith("vpn")
        or purpose in {"remote-user-vpn", "vpn-client", "vpn-server"}
        or "vpn" in vpn_type
        or "wireguard" in vpn_type
        or "openvpn" in vpn_type
    )


def classify_vpn_type(purpose: str, vpn_type: str) -> Tuple[bool, bool]:
    """Classify VPN configuration as client or server.

    Args:
        purpose: The purpose field from VPN config
        vpn_type: The vpn_type field from VPN config

    Returns:
        Tuple of (is_client, is_server)
    """
    purpose = str(purpose).lower() if purpose else ""
    vpn_type = str(vpn_type).lower() if vpn_type else ""

    is_client = purpose == "vpn-client" or "client" in vpn_type or vpn_type in {"wireguard-client", "openvpn-client"}

    is_server = (
        purpose in {"vpn-server", "remote-user-vpn"}
        or "server" in vpn_type
        or vpn_type in {"wireguard-server", "openvpn-server"}
    )

    return is_client, is_server


class VpnManager:
    """Manages VPN-related operations on the Unifi Controller.

    VPN configurations are retrieved from the networkconf API and filtered
    based on purpose and vpn_type fields.
    """

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize the VPN Manager.

        Args:
            connection_manager: The shared ConnectionManager instance.
        """
        self._connection = connection_manager

    async def _get_all_network_configs(self) -> List[Dict[str, Any]]:
        """Get all network configurations from the controller.

        Returns:
            List of network configuration dictionaries
        """
        cache_key = f"{CACHE_PREFIX_NETWORKS}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            api_request = ApiRequest(method="get", path="/rest/networkconf")
            response = await self._connection.request(api_request)

            # Handle various response formats
            if isinstance(response, dict) and "data" in response:
                networks = response["data"]
            elif isinstance(response, list):
                networks = response
            else:
                logger.warning(f"Unexpected networkconf response format: {type(response)}")
                networks = []

            self._connection._update_cache(cache_key, networks)
            return networks
        except Exception as e:
            logger.error(f"Error fetching network configurations: {e}")
            return []

    async def get_vpn_configs(self, include_clients: bool = True, include_servers: bool = True) -> List[Dict[str, Any]]:
        """Get VPN configurations from the controller.

        Args:
            include_clients: Whether to include VPN client configurations
            include_servers: Whether to include VPN server configurations

        Returns:
            List of VPN configuration dictionaries
        """
        cache_key = f"{CACHE_PREFIX_VPN_CONFIGS}_{self._connection.site}_{include_clients}_{include_servers}"
        cached_data = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            networks = await self._get_all_network_configs()
            vpn_configs = []

            for network in networks:
                if not is_vpn_network(network):
                    continue

                purpose = network.get("purpose", "")
                vpn_type = network.get("vpn_type", "")
                is_client, is_server = classify_vpn_type(purpose, vpn_type)

                if (include_clients and is_client) or (include_servers and is_server):
                    vpn_configs.append(network)
                    logger.debug(
                        f"Found VPN config: {network.get('name', 'unnamed')} "
                        f"(purpose={purpose}, vpn_type={vpn_type}, "
                        f"client={is_client}, server={is_server})"
                    )

            logger.debug(f"Found {len(vpn_configs)} VPN configurations")
            self._connection._update_cache(cache_key, vpn_configs)
            return vpn_configs

        except Exception as e:
            logger.error(f"Error getting VPN configurations: {e}")
            return []

    async def get_vpn_clients(self) -> List[Dict[str, Any]]:
        """Get list of VPN client configurations for the current site.

        Returns:
            List of VPN client configuration dictionaries
        """
        return await self.get_vpn_configs(include_clients=True, include_servers=False)

    async def get_vpn_servers(self) -> List[Dict[str, Any]]:
        """Get list of VPN server configurations for the current site.

        Returns:
            List of VPN server configuration dictionaries
        """
        return await self.get_vpn_configs(include_clients=False, include_servers=True)

    async def get_vpn_client_details(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific VPN client.

        Args:
            client_id: ID of the VPN client to get details for

        Returns:
            VPN client details if found, None otherwise
        """
        vpn_clients = await self.get_vpn_clients()
        client = next((c for c in vpn_clients if c.get("_id") == client_id), None)
        if not client:
            logger.warning(f"VPN client {client_id} not found")
        return client

    async def get_vpn_server_details(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific VPN server.

        Args:
            server_id: ID of the VPN server to get details for

        Returns:
            VPN server details if found, None otherwise
        """
        vpn_servers = await self.get_vpn_servers()
        server = next((s for s in vpn_servers if s.get("_id") == server_id), None)
        if not server:
            logger.warning(f"VPN server {server_id} not found")
        return server

    async def _update_vpn_config(self, config_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a VPN configuration.

        Args:
            config_id: ID of the VPN configuration to update
            update_data: Dictionary of fields to update (will be merged with existing)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Fetch existing config to merge with updates
            networks = await self._get_all_network_configs()
            existing = next((n for n in networks if n.get("_id") == config_id), None)

            if not existing:
                logger.error(f"VPN configuration {config_id} not found")
                return False

            # Merge updates into existing config
            merged_data = existing.copy()
            merged_data.update(update_data)

            api_request = ApiRequest(
                method="put",
                path=f"/rest/networkconf/{config_id}",
                data=merged_data,
            )
            await self._connection.request(api_request)

            logger.info(f"Updated VPN configuration {config_id}")

            # Invalidate caches
            self._connection._invalidate_cache(f"{CACHE_PREFIX_NETWORKS}_{self._connection.site}")
            # Also invalidate VPN-specific caches
            for suffix in ["_True_True", "_True_False", "_False_True"]:
                self._connection._invalidate_cache(f"{CACHE_PREFIX_VPN_CONFIGS}_{self._connection.site}{suffix}")

            return True

        except Exception as e:
            logger.error(f"Error updating VPN configuration {config_id}: {e}")
            return False

    async def update_vpn_client_state(self, client_id: str, enabled: bool) -> bool:
        """Update the enabled state of a VPN client.

        Args:
            client_id: ID of the VPN client to update
            enabled: Whether the client should be enabled or disabled

        Returns:
            True if successful, False otherwise
        """
        client = await self.get_vpn_client_details(client_id)
        if not client:
            logger.error(f"VPN client {client_id} not found, cannot update state")
            return False

        result = await self._update_vpn_config(client_id, {"enabled": enabled})
        if result:
            logger.info(f"VPN client {client.get('name', client_id)} {'enabled' if enabled else 'disabled'}")
        return result

    async def update_vpn_server_state(self, server_id: str, enabled: bool) -> bool:
        """Update the enabled state of a VPN server.

        Args:
            server_id: ID of the VPN server to update
            enabled: Whether the server should be enabled or disabled

        Returns:
            True if successful, False otherwise
        """
        server = await self.get_vpn_server_details(server_id)
        if not server:
            logger.error(f"VPN server {server_id} not found, cannot update state")
            return False

        result = await self._update_vpn_config(server_id, {"enabled": enabled})
        if result:
            logger.info(f"VPN server {server.get('name', server_id)} {'enabled' if enabled else 'disabled'}")
        return result

    async def toggle_vpn_config(self, config_id: str) -> bool:
        """Toggle a VPN configuration's enabled state.

        Args:
            config_id: ID of the VPN configuration to toggle

        Returns:
            True if successful, False otherwise
        """
        networks = await self._get_all_network_configs()
        config = next((n for n in networks if n.get("_id") == config_id), None)

        if not config or not is_vpn_network(config):
            logger.error(f"VPN configuration {config_id} not found")
            return False

        new_state = not config.get("enabled", True)
        return await self._update_vpn_config(config_id, {"enabled": new_state})
