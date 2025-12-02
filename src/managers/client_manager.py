import logging
from typing import List, Optional

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
            # Fallback rationale:
            # - Some controller models/versions may not populate the collection
            #   via controller.clients.update().
            # - UniFi API semantics: active/online clients are served from
            #   /stat/sta, while historical/all clients are under /rest/user.
            #   Therefore for "online" we fallback to GET /stat/sta.
            if not clients:
                try:
                    raw_clients = await self._connection.request(ApiRequest(method="get", path="/stat/sta"))
                    if isinstance(raw_clients, list) and raw_clients:
                        # Cache raw dicts; tool layer handles dict or Client
                        self._connection._update_cache(cache_key, raw_clients)
                        return raw_clients  # type: ignore[return-value]
                except Exception as fallback_e:
                    logger.debug(f"Raw clients fallback failed: {fallback_e}")
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
            # Fallback rationale:
            # - When the clients_all collection is empty, query the canonical
            #   UniFi endpoint for all/historical client records.
            # - UniFi API semantics: GET /rest/user returns all known clients
            #   (legacy naming "user" == client record), not only currently
            #   connected. This complements GET /stat/sta used for online-only.
            if not all_clients:
                try:
                    raw_all = await self._connection.request(ApiRequest(method="get", path="/rest/user"))
                    if isinstance(raw_all, list) and raw_all:
                        self._connection._update_cache(cache_key, raw_all)
                        return raw_all  # type: ignore[return-value]
                except Exception as fallback_e:
                    logger.debug(f"Raw all-clients fallback failed: {fallback_e}")
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
                data={"mac": client_mac, "cmd": "block-sta"},
            )
            # Call the updated request method
            await self._connection.request(api_request)
            logger.info(f"Block command sent for client {client_mac}")
            self._connection._invalidate_cache(f"{CACHE_PREFIX_CLIENTS}")  # Invalidate all client caches
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
                data={"mac": client_mac, "cmd": "unblock-sta"},
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

            api_request = ApiRequest(method="put", path=f"/upd/user/{client_id}", data={"name": name})
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
                data={"mac": client_mac, "cmd": "kick-sta"},
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
        self,
        client_mac: str,
        minutes: int,
        up_kbps: Optional[int] = None,
        down_kbps: Optional[int] = None,
        bytes_quota: Optional[int] = None,
    ) -> bool:
        """Authorize a guest client."""
        try:
            payload = {"mac": client_mac, "cmd": "authorize-guest", "minutes": minutes}
            if up_kbps is not None:
                payload["up"] = up_kbps
            if down_kbps is not None:
                payload["down"] = down_kbps
            if bytes_quota is not None:
                payload["bytes"] = bytes_quota

            # Construct ApiRequest
            api_request = ApiRequest(method="post", path="/cmd/stamgr", data=payload)
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
                data={"mac": client_mac, "cmd": "unauthorize-guest"},
            )
            await self._connection.request(api_request)
            logger.info(f"Unauthorize command sent for guest {client_mac}")
            self._connection._invalidate_cache(f"{CACHE_PREFIX_CLIENTS}")
            return True
        except Exception as e:
            logger.error(f"Error unauthorizing guest {client_mac}: {e}")
            return False

    async def set_client_ip_settings(
        self,
        client_mac: str,
        use_fixedip: Optional[bool] = None,
        fixed_ip: Optional[str] = None,
        local_dns_record_enabled: Optional[bool] = None,
        local_dns_record: Optional[str] = None,
    ) -> bool:
        """Set fixed IP and/or local DNS record for a client.

        Uses the UniFi REST API endpoint PUT /rest/user/{client_id}.
        Local DNS records require UniFi Network 7.2+.

        Args:
            client_mac: MAC address of the client to update.
            use_fixedip: Enable (True) or disable (False) fixed IP.
            fixed_ip: The fixed IP address to assign (required if use_fixedip=True).
            local_dns_record_enabled: Enable (True) or disable (False) local DNS.
            local_dns_record: The DNS hostname to assign (e.g., "mydevice.local").

        Returns:
            True if the update was successful, False otherwise.
        """
        try:
            # Get client to find their internal _id
            client = await self.get_client_details(client_mac)
            if not client:
                logger.error(f"Cannot set IP settings for {client_mac}: Client not found")
                return False

            client_raw = client.raw if hasattr(client, "raw") else client
            if "_id" not in client_raw:
                logger.error(f"Cannot set IP settings for {client_mac}: Missing _id")
                return False

            client_id = client_raw["_id"]

            # If client is not "noted" (known), mark it first to enable IP config
            if not client_raw.get("noted"):
                logger.info(f"Client {client_mac} not noted, marking as known first")
                note_payload = {"noted": True}
                if not client_raw.get("name") and client_raw.get("hostname"):
                    note_payload["name"] = client_raw["hostname"]
                try:
                    note_request = ApiRequest(
                        method="put",
                        path=f"/rest/user/{client_id}",
                        data=note_payload,
                    )
                    await self._connection.request(note_request)
                except Exception as note_err:
                    logger.warning(f"Could not mark client as noted: {note_err}")

            # Build payload with only explicitly provided fields
            payload: dict = {}

            if use_fixedip is not None:
                payload["use_fixedip"] = use_fixedip
                if use_fixedip and fixed_ip:
                    payload["fixed_ip"] = fixed_ip
                elif not use_fixedip:
                    payload["fixed_ip"] = ""
            elif fixed_ip is not None:
                # If only fixed_ip provided, assume enabling
                payload["use_fixedip"] = True
                payload["fixed_ip"] = fixed_ip

            if local_dns_record_enabled is not None:
                payload["local_dns_record_enabled"] = local_dns_record_enabled
                if local_dns_record_enabled and local_dns_record:
                    payload["local_dns_record"] = local_dns_record
                elif not local_dns_record_enabled:
                    payload["local_dns_record"] = ""
            elif local_dns_record is not None:
                # If only local_dns_record provided, assume enabling
                payload["local_dns_record_enabled"] = True
                payload["local_dns_record"] = local_dns_record

            if not payload:
                logger.warning(f"No IP settings provided for {client_mac}")
                return False

            api_request = ApiRequest(
                method="put",
                path=f"/rest/user/{client_id}",
                data=payload,
            )
            await self._connection.request(api_request)
            logger.info(f"IP settings updated for client {client_mac}: {payload}")
            self._connection._invalidate_cache(f"{CACHE_PREFIX_CLIENTS}")
            return True
        except Exception as e:
            logger.error(f"Error setting IP settings for {client_mac}: {e}")
            return False
