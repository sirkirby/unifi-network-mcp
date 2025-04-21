import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from aiounifi.models.api import ApiRequest
from aiounifi.models.event import Event # Import Event model
from aiounifi.models.dpi_restriction_app import DPIRestrictionApp # Import DPIApp model
from aiounifi.models.dpi_restriction_group import DPIRestrictionGroup # Import DPIGroup model
from .connection_manager import ConnectionManager
from .client_manager import ClientManager # Needed for get_top_clients

logger = logging.getLogger("unifi-network-mcp")

# Cache prefixes
CACHE_PREFIX_STATS_NETWORK = "stats_network"
CACHE_PREFIX_STATS_CLIENT = "stats_client"
CACHE_PREFIX_STATS_DEVICE = "stats_device"
CACHE_PREFIX_STATS_DPI = "stats_dpi"
CACHE_PREFIX_STATS_ALERTS = "stats_alerts"

class StatsManager:
    """Manages statistics retrieval from the Unifi Controller."""

    def __init__(self, connection_manager: ConnectionManager, client_manager: ClientManager):
        """Initialize the Stats Manager.

        Args:
            connection_manager: The shared ConnectionManager instance.
            client_manager: The ClientManager instance (needed for some stats methods).
        """
        self._connection = connection_manager
        self._client_manager = client_manager

    async def get_network_stats(self, duration_hours: int = 1) -> List[Dict[str, Any]]:
        """Get network statistics (e.g., hourly site stats)."""
        cache_key = f"{CACHE_PREFIX_STATS_NETWORK}_{duration_hours}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=300)  # 5 minute cache
        if cached_data is not None:
            return cached_data
            
        try:
            start_time = int((datetime.now() - timedelta(hours=duration_hours)).timestamp() * 1000)
            end_time = int(datetime.now().timestamp() * 1000)

            endpoint = "/stat/report/hourly.site"
            params = {
                "attrs": ["time", "rx_bytes-r", "tx_bytes-r", "wan-rx_bytes-r", "wan-tx_bytes-r", "wlan_bytes-r", "num_user"],
                "start": start_time,
                "end": end_time
            }
            api_request = ApiRequest(method="get", path=endpoint, params=params)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error(f"Error getting network stats: {e}")
            return []

    async def get_client_stats(self, client_mac: str, duration_hours: int = 1) -> List[Dict[str, Any]]:
        """Get statistics for a specific client."""
        cache_key = f"{CACHE_PREFIX_STATS_CLIENT}_{client_mac}_{duration_hours}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=300)  # 5 minute cache
        if cached_data is not None:
            return cached_data
            
        try:
            start_time = int((datetime.now() - timedelta(hours=duration_hours)).timestamp() * 1000)
            end_time = int(datetime.now().timestamp() * 1000)

            endpoint = "/stat/report/hourly.sta"
            params = {
                "attrs": ["time", "rx_bytes-r", "tx_bytes-r"],
                "mac": client_mac,
                "start": start_time,
                "end": end_time
            }
            api_request = ApiRequest(method="get", path=endpoint, params=params)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error(f"Error getting stats for client {client_mac}: {e}")
            return []

    async def get_device_stats(self, device_mac: str, duration_hours: int = 1) -> List[Dict[str, Any]]:
        """Get statistics for a specific device."""
        cache_key = f"{CACHE_PREFIX_STATS_DEVICE}_{device_mac}_{duration_hours}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=300)  # 5 minute cache
        if cached_data is not None:
            return cached_data
            
        try:
            start_time = int((datetime.now() - timedelta(hours=duration_hours)).timestamp() * 1000)
            end_time = int(datetime.now().timestamp() * 1000)

            endpoint = "/stat/report/hourly.dev"
            params = {
                "attrs": ["time", "rx_bytes-r", "tx_bytes-r", "num_sta"], # num_sta relevant for APs
                "mac": device_mac,
                "start": start_time,
                "end": end_time
            }
            api_request = ApiRequest(method="get", path=endpoint, params=params)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error(f"Error getting stats for device {device_mac}: {e}")
            return []

    async def get_top_clients(self, duration_hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top clients by usage. Requires fetching stats for all online clients."""
        online_clients = await self._client_manager.get_clients()
        if not online_clients:
            return []

        clients_raw = [c.raw if hasattr(c, "raw") else c for c in online_clients]

        client_stats_tasks = []
        valid_clients_for_stats = []
        for client in clients_raw:
            if client.get("mac"):
                client_stats_tasks.append(self.get_client_stats(client["mac"], duration_hours))
                valid_clients_for_stats.append(client)

        if not client_stats_tasks:
            return []

        all_client_stats_results = await asyncio.gather(*client_stats_tasks, return_exceptions=True)

        aggregated_stats: Dict[str, Dict[str, Any]] = {}
        for i, result in enumerate(all_client_stats_results):
            client_data = valid_clients_for_stats[i]
            mac = client_data.get("mac")

            if mac is None:
                continue
            if isinstance(result, Exception):
                logger.warning(f"Failed to get stats for client {mac}: {result}")
                continue
            if not result:
                continue

            total_rx = sum(s.get("rx_bytes-r", 0) for s in result)
            total_tx = sum(s.get("tx_bytes-r", 0) for s in result)
            aggregated_stats[mac] = {
                "mac": mac,
                "name": client_data.get("name") or client_data.get("hostname", mac),
                "rx_bytes": total_rx,
                "tx_bytes": total_tx,
                "total_bytes": total_rx + total_tx,
            }

        # Sort by total bytes descending and return top N
        sorted_clients = sorted(aggregated_stats.values(), key=lambda x: x["total_bytes"], reverse=True)
        return sorted_clients[:limit]

    async def get_dpi_stats(self) -> Dict[str, List[Any]]: # Return List[DPIRestrictionApp/Group]
        """Get Deep Packet Inspection (DPI) statistics."""
        cache_key = f"{CACHE_PREFIX_STATS_DPI}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=900)  # 15 minute cache
        if cached_data is not None:
            return cached_data
            
        if not await self._connection.ensure_connected() or not self._connection.controller:
            return {"applications": [], "categories": []}

        try:
            await self._connection.controller.dpi_apps.update()
            await self._connection.controller.dpi_groups.update()

            dpi_apps: List[DPIRestrictionApp] = list(self._connection.controller.dpi_apps.values())
            dpi_groups: List[DPIRestrictionGroup] = list(self._connection.controller.dpi_groups.values())
            result = {
                "applications": dpi_apps,
                "categories": dpi_groups
            }
            self._connection._update_cache(cache_key, result, timeout=900)
            return result
        except Exception as e:
            logger.error(f"Error getting DPI stats: {e}")
            return {"applications": [], "categories": []}

    async def get_alerts(self, include_archived: bool = False) -> List[Event]: # Changed return type
        """Get alerts from the controller."""
        cache_key = f"{CACHE_PREFIX_STATS_ALERTS}_{include_archived}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=60)  # 1 minute cache
        if cached_data is not None:
            return cached_data
            
        if not await self._connection.ensure_connected() or not self._connection.controller:
            return []

        try:
            await self._connection.controller.alerts.update()
            alerts: List[Event] = list(self._connection.controller.alerts.values())
            if not include_archived:
                alerts = [a for a in alerts if not a.raw.get("archived", False)]
            self._connection._update_cache(cache_key, alerts, timeout=60)
            return alerts
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return [] 