"""Hotspot Manager for UniFi Network MCP server.

Manages hotspot voucher operations including creation, listing, and revocation.
"""

import logging
from typing import Any, Dict, List, Optional

from aiounifi.models.api import ApiRequest

from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_VOUCHERS = "vouchers"


class HotspotManager:
    """Manages hotspot voucher operations on the UniFi Controller."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize the Hotspot Manager.

        Args:
            connection_manager: The shared ConnectionManager instance.
        """
        self._connection = connection_manager

    async def get_vouchers(self, create_time: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all hotspot vouchers for the current site.

        Uses GET /stat/voucher endpoint.

        Args:
            create_time: Optional Unix timestamp to filter by creation time.

        Returns:
            List of voucher objects containing code, quota, duration, etc.
        """
        cache_key = f"{CACHE_PREFIX_VOUCHERS}_{self._connection.site}"

        # Only use cache if no filter is applied
        if create_time is None:
            cached_data = self._connection.get_cached(cache_key)
            if cached_data is not None:
                return cached_data

        try:
            api_request = ApiRequest(method="get", path="/stat/voucher")
            response = await self._connection.request(api_request)

            vouchers = (
                response
                if isinstance(response, list)
                else response.get("data", [])
                if isinstance(response, dict)
                else []
            )

            # Filter by create_time if specified
            if create_time is not None:
                vouchers = [v for v in vouchers if v.get("create_time") == create_time]
            else:
                self._connection._update_cache(cache_key, vouchers)

            return vouchers
        except Exception as e:
            logger.error(f"Error getting vouchers: {e}")
            return []

    async def get_voucher_details(self, voucher_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific voucher by ID.

        Args:
            voucher_id: The _id of the voucher.

        Returns:
            Voucher object or None if not found.
        """
        try:
            all_vouchers = await self.get_vouchers()
            voucher = next((v for v in all_vouchers if v.get("_id") == voucher_id), None)
            if not voucher:
                logger.debug(f"Voucher {voucher_id} not found.")
            return voucher
        except Exception as e:
            logger.error(f"Error getting voucher details for {voucher_id}: {e}")
            return None

    async def create_voucher(
        self,
        expire_minutes: int,
        count: int = 1,
        quota: int = 1,
        note: Optional[str] = None,
        up_limit_kbps: Optional[int] = None,
        down_limit_kbps: Optional[int] = None,
        bytes_limit_mb: Optional[int] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """Create one or more hotspot vouchers.

        Uses POST to /cmd/hotspot with create-voucher command.

        Args:
            expire_minutes: Minutes the voucher is valid after activation.
            count: Number of vouchers to create (default 1).
            quota: Usage quota - 0 for multi-use, 1 for single-use,
                   n for n-times usable (default 1).
            note: Optional note for the voucher (visible when printed).
            up_limit_kbps: Optional upload speed limit in Kbps.
            down_limit_kbps: Optional download speed limit in Kbps.
            bytes_limit_mb: Optional data transfer limit in MB.

        Returns:
            List of created voucher objects, or None on failure.
        """
        try:
            payload: Dict[str, Any] = {
                "cmd": "create-voucher",
                "expire": expire_minutes,
                "n": count,
                "quota": quota,
            }

            if note:
                payload["note"] = note
            if up_limit_kbps is not None:
                payload["up"] = up_limit_kbps
            if down_limit_kbps is not None:
                payload["down"] = down_limit_kbps
            if bytes_limit_mb is not None:
                payload["bytes"] = bytes_limit_mb

            api_request = ApiRequest(
                method="post",
                path="/cmd/hotspot",
                data=payload,
            )
            response = await self._connection.request(api_request)

            logger.info(f"Create voucher: {count} voucher(s), {expire_minutes} min, quota={quota}")

            # Invalidate cache
            self._connection._invalidate_cache(f"{CACHE_PREFIX_VOUCHERS}_{self._connection.site}")

            # Response contains create_time to fetch newly created vouchers
            if isinstance(response, list) and len(response) > 0:
                create_time = response[0].get("create_time")
                if create_time:
                    return await self.get_vouchers(create_time=create_time)
                return response
            elif isinstance(response, dict):
                create_time = response.get("create_time")
                if create_time:
                    return await self.get_vouchers(create_time=create_time)
                return [response] if response else None

            # Fallback: return all vouchers if we can't identify the new ones
            return await self.get_vouchers()

        except Exception as e:
            logger.error(f"Error creating voucher: {e}", exc_info=True)
            return None

    async def revoke_voucher(self, voucher_id: str) -> bool:
        """Revoke/delete a voucher by its ID.

        Uses POST to /cmd/hotspot with delete-voucher command.

        Args:
            voucher_id: The _id of the voucher to revoke.

        Returns:
            True if successful, False otherwise.
        """
        try:
            api_request = ApiRequest(
                method="post",
                path="/cmd/hotspot",
                data={
                    "cmd": "delete-voucher",
                    "_id": voucher_id,
                },
            )
            await self._connection.request(api_request)

            logger.info(f"Revoked voucher {voucher_id}")

            # Invalidate cache
            self._connection._invalidate_cache(f"{CACHE_PREFIX_VOUCHERS}_{self._connection.site}")

            return True

        except Exception as e:
            logger.error(f"Error revoking voucher {voucher_id}: {e}", exc_info=True)
            return False
