import logging
from typing import Dict, List, Optional, Any

from aiounifi.models.api import ApiRequest
from aiounifi.models.client import Client
from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_CLIENTS = "clients"

class ClientManager:
    """Manages client-related operations on the Unifi Controller."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize the Client Manager.

        Args:
            connection_manager: The shared ConnectionManager instance.
        """
        self._connection = connection_manager

    async def get_clients(self) -> List[Client]:
        """Get list of currently online clients for the current site."""
        if not await self._connection.ensure_connected() or not self._connection.controller:
            return []

        cache_key = f"{CACHE_PREFIX_CLIENTS}_online_{self._connection.site}"
        cached_data: Optional[List[Client]] = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            await self._connection.controller.clients.update()
            clients: List[Client] = list(self._connection.controller.clients.values())
            self._connection._update_cache(cache_key, clients)
            return clients
        except Exception as e:
            logger.error(f"Error getting online clients: {e}")
            return []

    async def get_all_clients(self) -> List[Client]:
        """Get list of all clients (including offline/historical) for the current site."""
        if not await self._connection.ensure_connected() or not self._connection.controller:
            return []

        cache_key = f"{CACHE_PREFIX_CLIENTS}_all_{self._connection.site}"
        cached_data: Optional[List[Client]] = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            await self._connection.controller.clients_all.update()
            all_clients: List[Client] = list(self._connection.controller.clients_all.values())
            self._connection._update_cache(cache_key, all_clients)
            return all_clients
        except Exception as e:
            logger.error(f"Error getting all clients: {e}")
            return []

    async def get_client_details(self, client_mac: str) -> Optional[Client]:
        """Get detailed information for a specific client by MAC address."""
        all_clients = await self.get_all_clients()
        client: Optional[Client] = next((c for c in all_clients if c.mac == client_mac), None)
        if not client:
             logger.debug(f"Client details for MAC {client_mac} not found in clients_all list.")
        return client

    async def block_client(self, client_mac: str) -> bool:
        """Block a client by MAC address."""
        try:
            # Construct ApiRequest
            api_request = ApiRequest(
                method="post",
                path="/cmd/stamgr",
                json={"mac": client_mac, "cmd": "block-sta"}
            )
            # Call the updated request method
            await self._connection.request(api_request)
            logger.info(f"Block command sent for client {client_mac}")
            self._connection._invalidate_cache(f"{CACHE_PREFIX_CLIENTS}") # Invalidate all client caches
            return True
        except Exception as e:
            logger.error(f"Error blocking client {client_mac}: {e}")
            return False

    async def unblock_client(self, client_mac: str) -> bool:
        """Unblock a client by MAC address."""
        try:
            # Construct ApiRequest
            api_request = ApiRequest(
                method="post",
                path="/cmd/stamgr",
                json={"mac": client_mac, "cmd": "unblock-sta"}
            )
            # Call the updated request method
            await self._connection.request(api_request)
            logger.info(f"Unblock command sent for client {client_mac}")
            self._connection._invalidate_cache(f"{CACHE_PREFIX_CLIENTS}")
            return True
        except Exception as e:
            logger.error(f"Error unblocking client {client_mac}: {e}")
            return False

    async def rename_client(self, client_mac: str, name: str) -> bool:
        """Rename a client device."""
        try:
            client = await self.get_client_details(client_mac)
            if not client or "_id" not in client.raw:
                logger.error(f"Cannot rename client {client_mac}: Not found or missing ID.")
                return False
            client_id = client.raw["_id"]

            api_request = ApiRequest(
                method="put",
                path=f"/upd/user/{client_id}",
                json={"name": name}
            )
            await self._connection.request(api_request)
            logger.info(f"Rename command sent for client {client_mac} to '{name}'")
            self._connection._invalidate_cache(f"{CACHE_PREFIX_CLIENTS}")
            return True
        except Exception as e:
            logger.error(f"Error renaming client {client_mac} to '{name}': {e}")
            return False

    async def force_reconnect_client(self, client_mac: str) -> bool:
        """Force a client to reconnect (kick)."""
        try:
            api_request = ApiRequest(
                method="post",
                path="/cmd/stamgr",
                json={"mac": client_mac, "cmd": "kick-sta"}
            )
            await self._connection.request(api_request)
            logger.info(f"Force reconnect (kick) command sent for client {client_mac}")
            self._connection._invalidate_cache(f"{CACHE_PREFIX_CLIENTS}")
            return True
        except Exception as e:
            logger.error(f"Error forcing reconnect for client {client_mac}: {e}")
            return False

    async def get_blocked_clients(self) -> List[Client]:
        """Get a list of currently blocked clients."""
        all_clients = await self.get_all_clients()
        blocked: List[Client] = [client for client in all_clients if client.blocked]
        return blocked

    async def authorize_guest(
        self, client_mac: str, minutes: int,
        up_kbps: Optional[int]=None, down_kbps: Optional[int]=None,
        bytes_quota: Optional[int]=None
    ) -> bool:
        """Authorize a guest client."""
        try:
            payload = {
                "mac": client_mac,
                "cmd": "authorize-guest",
                "minutes": minutes
            }
            if up_kbps is not None:
                payload['up'] = up_kbps
            if down_kbps is not None:
                payload['down'] = down_kbps
            if bytes_quota is not None:
                payload['bytes'] = bytes_quota

            # Construct ApiRequest
            api_request = ApiRequest(
                method="post",
                path="/cmd/stamgr",
                json=payload
            )
            # Call the updated request method
            await self._connection.request(api_request)
            logger.info(f"Authorize command sent for guest {client_mac} for {minutes} minutes")
            self._connection._invalidate_cache(f"{CACHE_PREFIX_CLIENTS}")
            return True
        except Exception as e:
            logger.error(f"Error authorizing guest {client_mac}: {e}")
            return False

    async def unauthorize_guest(self, client_mac: str) -> bool:
        """Unauthorize (de-authorize) a guest client."""
        try:
            api_request = ApiRequest(
                method="post",
                path="/cmd/stamgr",
                json={"mac": client_mac, "cmd": "unauthorize-guest"}
            )
            await self._connection.request(api_request)
            logger.info(f"Unauthorize command sent for guest {client_mac}")
            self._connection._invalidate_cache(f"{CACHE_PREFIX_CLIENTS}")
            return True
        except Exception as e:
            logger.error(f"Error unauthorizing guest {client_mac}: {e}")
            return False 