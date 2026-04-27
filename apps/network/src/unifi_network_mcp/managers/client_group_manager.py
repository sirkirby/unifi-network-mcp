"""Manager for client groups (network member groups) on the UniFi controller.

Client groups organize devices by MAC address for use in OON policies,
firewall rules, and other network configurations. Groups have a name,
type (CLIENTS), and a list of member MAC addresses.

API endpoint: /proxy/network/v2/api/site/{site}/network-members-group
"""

import logging
from typing import Any, Dict, List, Optional

from aiounifi.models.api import ApiRequestV2

from unifi_core.merge import deep_merge

from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_CLIENT_GROUPS = "client_groups"


class ClientGroupManager:
    """Manages client groups (network member groups) on the UniFi controller."""

    def __init__(self, connection_manager: ConnectionManager):
        self._connection = connection_manager

    async def get_client_groups(self) -> List[Dict[str, Any]]:
        """Get all client groups.

        Returns:
            List of client group dictionaries.
        """
        cache_key = f"{CACHE_PREFIX_CLIENT_GROUPS}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        if not await self._connection.ensure_connected():
            raise ConnectionError("Not connected to controller")
        try:
            api_request = ApiRequestV2(method="get", path="/network-members-groups")
            response = await self._connection.request(api_request)

            groups = (
                response
                if isinstance(response, list)
                else response.get("data", [])
                if isinstance(response, dict)
                else []
            )

            self._connection._update_cache(cache_key, groups)
            return groups
        except Exception as e:
            logger.error("Error getting client groups: %s", e)
            raise

    async def get_client_group_by_id(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific client group by ID.

        Args:
            group_id: The ID of the client group.

        Returns:
            The client group dictionary, or None if not found.
        """
        if not await self._connection.ensure_connected():
            raise ConnectionError("Not connected to controller")

        try:
            api_request = ApiRequestV2(method="get", path=f"/network-members-group/{group_id}")
            response = await self._connection.request(api_request)

            if isinstance(response, list):
                return response[0] if response else None
            if isinstance(response, dict):
                return response if "id" in response or "_id" in response else response.get("data", None)
            return None
        except Exception as e:
            logger.error("Error getting client group %s: %s", group_id, e)
            raise

    async def create_client_group(self, group_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new client group.

        Args:
            group_data: Dictionary containing the group configuration.
                Required fields:
                - name (str): Group name
                - members (list): List of MAC addresses
                - type (str): "CLIENTS"

        Returns:
            The created client group dictionary, or None on failure.
        """
        if not await self._connection.ensure_connected():
            raise ConnectionError("Not connected to controller")

        required_keys = {"name", "members", "type"}
        missing = required_keys - group_data.keys()
        if missing:
            logger.error("Missing required keys for client group: %s", missing)
            return None

        try:
            api_request = ApiRequestV2(method="post", path="/network-members-group", data=group_data)
            response = await self._connection.request(api_request)

            self._invalidate_cache()

            if isinstance(response, dict) and ("id" in response or "_id" in response):
                return response
            elif isinstance(response, dict) and "data" in response:
                return response["data"]
            elif isinstance(response, list) and len(response) > 0:
                return response[0] if isinstance(response[0], dict) else {"id": str(response[0])}
            elif response is None or response == "":
                logger.info("Create returned empty response, verifying via list")
                groups = await self.get_client_groups()
                created = next(
                    (g for g in groups if g.get("name") == group_data.get("name")),
                    None,
                )
                return created
            else:
                logger.error("Unexpected response creating client group: %s %s", type(response), response)
                return None
        except Exception as e:
            logger.error("Error creating client group: %s", e, exc_info=True)
            raise

    async def update_client_group(self, group_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an existing client group by merging updates with current state.

        Args:
            group_id: The ID of the client group to update.
            update_data: Dictionary of fields to update (partial is fine).

        Returns:
            True on success, False on failure.
        """
        if not await self._connection.ensure_connected():
            raise ConnectionError("Not connected to controller")
        if not update_data:
            return True

        try:
            existing = await self.get_client_group_by_id(group_id)
            if not existing:
                logger.error("Client group %s not found for update", group_id)
                return False

            merged_data = deep_merge(existing, update_data)

            api_request = ApiRequestV2(method="put", path=f"/network-members-group/{group_id}", data=merged_data)
            await self._connection.request(api_request)

            self._invalidate_cache()
            return True
        except Exception as e:
            logger.error("Error updating client group %s: %s", group_id, e, exc_info=True)
            raise

    async def delete_client_group(self, group_id: str) -> bool:
        """Delete a client group.

        Args:
            group_id: The ID of the client group to delete.

        Returns:
            True on success, False on failure.
        """
        if not await self._connection.ensure_connected():
            raise ConnectionError("Not connected to controller")

        try:
            api_request = ApiRequestV2(method="delete", path=f"/network-members-group/{group_id}")
            await self._connection.request(api_request)

            self._invalidate_cache()
            return True
        except Exception as e:
            logger.error("Error deleting client group %s: %s", group_id, e, exc_info=True)
            raise

    def _invalidate_cache(self):
        """Invalidate all client group caches."""
        self._connection._invalidate_cache(CACHE_PREFIX_CLIENT_GROUPS)
