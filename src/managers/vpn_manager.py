import logging
from typing import Dict, List, Optional, Any

from aiounifi.models.api import ApiRequest
from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_VPN_SERVERS = "vpn_servers"
CACHE_PREFIX_VPN_CLIENTS = "vpn_clients"

class VpnManager:
    """Manages VPN-related operations on the Unifi Controller."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize the VPN Manager.

        Args:
            connection_manager: The shared ConnectionManager instance.
        """
        self._connection = connection_manager

    async def get_vpn_servers(self) -> List[Dict[str, Any]]:
        """Get list of VPN servers for the current site."""
        cache_key = f"{CACHE_PREFIX_VPN_SERVERS}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            api_request = ApiRequest(method="get", path="/rest/vpnserver")
            response = await self._connection.request(api_request)
            servers = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, servers)
            return servers
        except Exception as e:
            logger.error(f"Error getting VPN servers: {e}")
            return []

    async def get_vpn_server_details(self, server_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific VPN server."""
        vpn_servers = await self.get_vpn_servers()
        server = next((s for s in vpn_servers if s.get("_id") == server_id), None)
        if not server:
            logger.warning(f"VPN server {server_id} not found in cached/fetched list.")
        return server

    async def update_vpn_server_state(self, server_id: str, enabled: bool) -> bool:
        """Update the enabled state of a VPN server.

        Args:
            server_id: ID of the server to update
            enabled: Whether the server should be enabled or disabled

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            server = await self.get_vpn_server_details(server_id)
            if not server:
                logger.error(f"VPN server {server_id} not found, cannot update state")
                return False
            
            update_data = {"enabled": enabled}
            
            api_request = ApiRequest(
                method="put",
                path=f"/rest/vpnserver/{server_id}",
                json=update_data
            )
            await self._connection.request(api_request)
            logger.info(f"Update state command sent for VPN server {server_id} (enabled={enabled})")
            self._connection._invalidate_cache(f"{CACHE_PREFIX_VPN_SERVERS}_{self._connection.site}")
            return True
        except Exception as e:
            logger.error(f"Error updating VPN server state {server_id}: {e}")
            return False

    async def get_vpn_clients(self) -> List[Dict[str, Any]]:
        """Get list of active VPN clients for the current site."""
        cache_key = f"{CACHE_PREFIX_VPN_CLIENTS}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=30)  # 30 second cache
        if cached_data is not None:
            return cached_data
            
        try:
            api_request = ApiRequest(method="get", path="/stat/vpn")
            response = await self._connection.request(api_request)
            clients = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, clients, timeout=30)
            return clients
        except Exception as e:
            logger.error(f"Error getting VPN clients: {e}")
            return []

    async def get_vpn_client_details(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific VPN client.
        
        Args:
            client_id: ID of the client to get details for
            
        Returns:
            Client details if found, None otherwise
        """
        vpn_clients = await self.get_vpn_clients()
        client = next((c for c in vpn_clients if c.get("_id") == client_id), None)
        if not client:
            logger.warning(f"VPN client {client_id} not found in fetched list.")
        return client

    async def update_vpn_client_state(self, client_id: str, enabled: bool) -> bool:
        """Update the enabled state of a VPN client.
        
        Args:
            client_id: ID of the client to update
            enabled: Whether the client should be enabled or disabled
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            client = await self.get_vpn_client_details(client_id)
            if not client:
                logger.error(f"VPN client {client_id} not found, cannot update state")
                return False
            
            update_data = {"enabled": enabled}
            
            api_request = ApiRequest(
                method="put",
                path=f"/rest/vpnclient/{client_id}",
                json=update_data
            )
            
            try:
                await self._connection.request(api_request)
                logger.info(f"Update state command sent for VPN client {client_id} (enabled={enabled})")
                self._connection._invalidate_cache(f"{CACHE_PREFIX_VPN_CLIENTS}_{self._connection.site}")
                return True
            except Exception as e:
                logger.error(f"API error updating VPN client state {client_id}: {e}")
                return await self._update_vpn_client_state_alternative(client_id, enabled)
                
        except Exception as e:
            logger.error(f"Error updating VPN client state {client_id}: {e}")
            return False


    async def generate_vpn_client_profile(
        self,
        server_id: str,
        client_name: str,
        expiration_days: Optional[int] = 365
    ) -> Optional[str]:
        """Generate a client profile configuration for VPN connection.

        Args:
            server_id: ID of the VPN server
            client_name: Name for the client configuration
            expiration_days: Days until the profile expires (default: 365)

        Returns:
            Client profile configuration (often as a string) if successful, None otherwise
        """
        try:
            server = await self.get_vpn_server_details(server_id)
            if not server:
                logger.error(f"Cannot generate profile for non-existent server {server_id}")
                return None

            payload = {
                "name": client_name,
                "server_id": server_id,
                "exp": expiration_days
            }

            api_request = ApiRequest(
                method="post",
                path="/rest/vpnprofile",
                json=payload
            )
            response = await self._connection.request(api_request)
            logger.info(f"Generate profile command sent for VPN client '{client_name}' on server {server_id}")

            if isinstance(response, dict) and "data" in response:
                profile_data = response["data"]
                if isinstance(profile_data, list) and len(profile_data) > 0:
                    return str(profile_data[0]) # Return first element as string
                return str(profile_data) # Return data as string
            elif isinstance(response, str):
                return response # Handle cases where API returns profile directly as string

            logger.warning(f"Could not extract VPN client profile data from response: {response}")
            return str(response) # Return raw response as string if extraction fails
        except Exception as e:
            logger.error(f"Error generating VPN client profile: {e}")
            return None 