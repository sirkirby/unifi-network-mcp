import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from aiounifi.models.api import ApiRequest
from aiounifi.models.dpi_restriction_app import DPIRestrictionApp  # Import DPIApp model
from aiounifi.models.dpi_restriction_group import (
    DPIRestrictionGroup,
)  # Import DPIGroup model
from aiounifi.models.event import Event  # Import Event model

from .client_manager import ClientManager  # Needed for get_top_clients
from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

# Cache prefixes
CACHE_PREFIX_STATS_NETWORK = "stats_network"
CACHE_PREFIX_STATS_CLIENT = "stats_client"
CACHE_PREFIX_STATS_DEVICE = "stats_device"
CACHE_PREFIX_STATS_DPI = "stats_dpi"
CACHE_PREFIX_STATS_ALERTS = "stats_alerts"
CACHE_PREFIX_STATS_GATEWAY = "stats_gateway"
CACHE_PREFIX_STATS_SPEEDTEST = "stats_speedtest"
CACHE_PREFIX_STATS_SITE_DPI = "stats_site_dpi"
CACHE_PREFIX_STATS_CLIENT_DPI = "stats_client_dpi"
CACHE_PREFIX_STATS_IPS = "stats_ips"
CACHE_PREFIX_STATS_SESSIONS = "stats_sessions"
CACHE_PREFIX_STATS_DASHBOARD = "stats_dashboard"
CACHE_PREFIX_STATS_ANOMALIES = "stats_anomalies"
CACHE_PREFIX_STATS_CLIENT_WIFI = "stats_client_wifi"

# Granularity validation
VALID_GRANULARITIES = {"5minutes", "hourly", "daily", "monthly"}


def _resolve_granularity(granularity: str) -> str:
    """Validate and return the granularity string.

    Args:
        granularity: One of 5minutes, hourly, daily, monthly.

    Returns:
        The validated granularity string.

    Raises:
        ValueError: If the granularity is not valid.
    """
    if granularity not in VALID_GRANULARITIES:
        raise ValueError(
            f"Invalid granularity '{granularity}'. Must be one of: {', '.join(sorted(VALID_GRANULARITIES))}"
        )
    return granularity


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

    async def get_network_stats(self, duration_hours: int = 1, granularity: str = "hourly") -> List[Dict[str, Any]]:
        """Get network statistics (e.g., hourly site stats)."""
        granularity = _resolve_granularity(granularity)
        cache_key = f"{CACHE_PREFIX_STATS_NETWORK}_{duration_hours}_{granularity}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=300)  # 5 minute cache
        if cached_data is not None:
            return cached_data

        try:
            start_time = int((datetime.now() - timedelta(hours=duration_hours)).timestamp() * 1000)
            end_time = int(datetime.now().timestamp() * 1000)

            endpoint = f"/stat/report/{granularity}.site"
            # Use non-rate attributes commonly available on report endpoints
            payload = {
                "attrs": [
                    "bytes",  # total bytes (if provided by controller)
                    "rx_bytes",  # some controllers provide rx/tx at site level
                    "tx_bytes",
                    "num_user",
                    "num_sta",
                    "num_active_user",
                    "wan-rx_bytes",
                    "wan-tx_bytes",
                    "wlan-num_sta",
                    "lan-num_sta",
                ],
                "start": start_time,
                "end": end_time,
            }
            api_request = ApiRequest(method="post", path=endpoint, data=payload)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error("Error getting network stats: %s", e)
            return []

    async def get_client_stats(
        self, client_mac: str, duration_hours: int = 1, granularity: str = "hourly"
    ) -> List[Dict[str, Any]]:
        """Get statistics for a specific client."""
        granularity = _resolve_granularity(granularity)
        cache_key = f"{CACHE_PREFIX_STATS_CLIENT}_{client_mac}_{duration_hours}_{granularity}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=300)  # 5 minute cache
        if cached_data is not None:
            return cached_data

        try:
            start_time = int((datetime.now() - timedelta(hours=duration_hours)).timestamp() * 1000)
            end_time = int(datetime.now().timestamp() * 1000)

            endpoint = f"/stat/report/{granularity}.user"
            payload = {
                "attrs": [
                    "rx_bytes",
                    "tx_bytes",
                    "bytes",
                    "signal",
                    "satisfaction",
                    "tx_retries",
                    "tx_rate",
                    "rx_rate",
                    "wifi_tx_attempts",
                ],
                "mac": client_mac,
                "start": start_time,
                "end": end_time,
            }
            api_request = ApiRequest(method="post", path=endpoint, data=payload)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error("Error getting stats for client %s: %s", client_mac, e)
            return []

    async def get_device_stats(
        self,
        device_mac: str,
        duration_hours: int = 1,
        granularity: str = "hourly",
        device_type: str = "dev",
    ) -> List[Dict[str, Any]]:
        """Get statistics for a specific device.

        Args:
            device_mac: MAC address of the device.
            duration_hours: Number of hours to look back.
            granularity: Report granularity (5minutes, hourly, daily, monthly).
            device_type: Device type for endpoint routing (ap, gw, or dev).
        """
        granularity = _resolve_granularity(granularity)
        cache_key = (
            f"{CACHE_PREFIX_STATS_DEVICE}_{device_mac}_{duration_hours}_{granularity}"
            f"_{device_type}_{self._connection.site}"
        )
        cached_data = self._connection.get_cached(cache_key, timeout=300)  # 5 minute cache
        if cached_data is not None:
            return cached_data

        try:
            start_time = int((datetime.now() - timedelta(hours=duration_hours)).timestamp() * 1000)
            end_time = int(datetime.now().timestamp() * 1000)

            # Route endpoint and attrs based on device_type
            if device_type == "ap":
                endpoint = f"/stat/report/{granularity}.ap"
                attrs = [
                    "num_sta",
                    "ng-num_sta",
                    "na-num_sta",
                    "satisfaction",
                    "tx_retries",
                    "wifi_tx_attempts",
                    "wifi_tx_dropped",
                    "ng-tx_bytes",
                    "na-tx_bytes",
                    "ng-rx_bytes",
                    "na-rx_bytes",
                ]
            elif device_type == "gw":
                endpoint = f"/stat/report/{granularity}.gw"
                attrs = [
                    "wan-rx_bytes",
                    "wan-tx_bytes",
                    "lan-rx_bytes",
                    "lan-tx_bytes",
                    "cpu",
                    "mem",
                    "loadavg_5",
                ]
            else:
                endpoint = f"/stat/report/{granularity}.dev"
                attrs = [
                    "rx_bytes",
                    "tx_bytes",
                    "bytes",
                    "num_sta",
                ]

            payload = {
                "attrs": attrs,
                "mac": device_mac,
                "start": start_time,
                "end": end_time,
            }
            api_request = ApiRequest(method="post", path=endpoint, data=payload)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error("Error getting stats for device %s: %s", device_mac, e)
            return []

    async def get_top_clients(self, duration_hours: int = 24, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top clients by usage.

        Fallback approach: derive usage from current client objects when report
        endpoints return no data. Values are cumulative since association and
        are sufficient for ranking purposes.
        """
        online_clients = await self._client_manager.get_clients()
        if not online_clients:
            return []

        clients_raw = [c.raw if hasattr(c, "raw") else c for c in online_clients]

        aggregated_stats: List[Dict[str, Any]] = []

        def _safe_int(value: Any) -> int:
            try:
                if value is None:
                    return 0
                if isinstance(value, bool):
                    return int(value)
                return int(str(value))
            except Exception:
                return 0

        for client in clients_raw:
            mac = client.get("mac")
            if not mac:
                continue

            # Prefer explicit total if present, otherwise sum rx/tx (wifi + wired)
            rx = _safe_int(client.get("rx_bytes")) + _safe_int(
                client.get("wired_rx_bytes") or client.get("wired-rx_bytes")
            )
            tx = _safe_int(client.get("tx_bytes")) + _safe_int(
                client.get("wired_tx_bytes") or client.get("wired-tx_bytes")
            )
            total = _safe_int(client.get("bytes")) or (rx + tx)

            aggregated_stats.append(
                {
                    "mac": mac,
                    "name": client.get("name") or client.get("hostname", mac),
                    "rx_bytes": rx,
                    "tx_bytes": tx,
                    "total_bytes": total,
                }
            )

        # Sort by total bytes descending and return top N
        sorted_clients = sorted(aggregated_stats, key=lambda x: x["total_bytes"], reverse=True)
        return sorted_clients[:limit]

    async def get_dpi_stats(
        self,
    ) -> Dict[str, List[Any]]:  # Return List[DPIRestrictionApp/Group]
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
            result = {"applications": dpi_apps, "categories": dpi_groups}
            self._connection._update_cache(cache_key, result, timeout=900)
            return result
        except Exception as e:
            logger.error("Error getting DPI stats: %s", e)
            return {"applications": [], "categories": []}

    async def get_alerts(self, include_archived: bool = False) -> List[Event]:  # Changed return type
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
            logger.error("Error getting alerts: %s", e)
            return []

    async def get_gateway_stats(self, duration_hours: int = 24, granularity: str = "hourly") -> List[Dict[str, Any]]:
        """Get gateway statistics."""
        granularity = _resolve_granularity(granularity)
        cache_key = f"{CACHE_PREFIX_STATS_GATEWAY}_{duration_hours}_{granularity}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=300)  # 5 minute cache
        if cached_data is not None:
            return cached_data

        try:
            start_time = int((datetime.now() - timedelta(hours=duration_hours)).timestamp() * 1000)
            end_time = int(datetime.now().timestamp() * 1000)

            endpoint = f"/stat/report/{granularity}.gw"
            payload = {
                "attrs": [
                    "wan-rx_bytes",
                    "wan-tx_bytes",
                    "lan-rx_bytes",
                    "lan-tx_bytes",
                    "cpu",
                    "mem",
                    "loadavg_5",
                    "wan-rx_packets",
                    "wan-tx_packets",
                ],
                "start": start_time,
                "end": end_time,
            }
            api_request = ApiRequest(method="post", path=endpoint, data=payload)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error("Error getting gateway stats: %s", e)
            return []

    async def get_speedtest_results(self, duration_hours: int = 24) -> List[Dict[str, Any]]:
        """Get speed test results from the controller archive."""
        cache_key = f"{CACHE_PREFIX_STATS_SPEEDTEST}_{duration_hours}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=300)  # 5 minute cache
        if cached_data is not None:
            return cached_data

        try:
            start_time = int((datetime.now() - timedelta(hours=duration_hours)).timestamp() * 1000)
            end_time = int(datetime.now().timestamp() * 1000)

            endpoint = "/stat/report/archive.speedtest"
            payload = {
                "attrs": [
                    "xput_download",
                    "xput_upload",
                    "latency",
                    "time",
                ],
                "start": start_time,
                "end": end_time,
            }
            api_request = ApiRequest(method="post", path=endpoint, data=payload)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error("Error getting speedtest results: %s", e)
            return []

    async def get_site_dpi_traffic(self, by: str = "by_app") -> List[Dict[str, Any]]:
        """Get site-level DPI traffic statistics.

        Args:
            by: Grouping type, e.g. 'by_app' or 'by_cat'.
        """
        cache_key = f"{CACHE_PREFIX_STATS_SITE_DPI}_{by}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=900)  # 15 minute cache
        if cached_data is not None:
            return cached_data

        try:
            endpoint = "/stat/sitedpi"
            payload = {"type": by}
            api_request = ApiRequest(method="post", path=endpoint, data=payload)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=900)
            return result
        except Exception as e:
            logger.error("Error getting site DPI traffic: %s", e)
            return []

    async def get_client_dpi_traffic(self, client_mac: str, by: str = "by_app") -> List[Dict[str, Any]]:
        """Get DPI traffic statistics for a specific client.

        Args:
            client_mac: MAC address of the client.
            by: Grouping type, e.g. 'by_app' or 'by_cat'.
        """
        cache_key = f"{CACHE_PREFIX_STATS_CLIENT_DPI}_{client_mac}_{by}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=900)  # 15 minute cache
        if cached_data is not None:
            return cached_data

        try:
            endpoint = "/stat/stadpi"
            payload = {"type": by, "macs": [client_mac]}
            api_request = ApiRequest(method="post", path=endpoint, data=payload)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=900)
            return result
        except Exception as e:
            logger.error("Error getting DPI traffic for client %s: %s", client_mac, e)
            return []

    async def get_ips_events(self, duration_hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        """Get IPS/IDS events.

        Args:
            duration_hours: Number of hours to look back.
            limit: Maximum number of events to return.
        """
        cache_key = f"{CACHE_PREFIX_STATS_IPS}_{duration_hours}_{limit}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=300)  # 5 minute cache
        if cached_data is not None:
            return cached_data

        try:
            start_time = int((datetime.now() - timedelta(hours=duration_hours)).timestamp() * 1000)
            end_time = int(datetime.now().timestamp() * 1000)

            endpoint = "/stat/ips/event"
            payload = {
                "start": start_time,
                "end": end_time,
                "_limit": limit,
            }
            api_request = ApiRequest(method="post", path=endpoint, data=payload)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error("Error getting IPS events: %s", e)
            return []

    async def get_client_sessions(
        self,
        client_mac: Optional[str] = None,
        duration_hours: int = 24,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get client session history.

        Args:
            client_mac: Optional MAC address to filter sessions for a specific client.
            duration_hours: Number of hours to look back.
            limit: Maximum number of sessions to return.
        """
        mac_part = client_mac or "all"
        cache_key = f"{CACHE_PREFIX_STATS_SESSIONS}_{mac_part}_{duration_hours}_{limit}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=300)  # 5 minute cache
        if cached_data is not None:
            return cached_data

        try:
            start_time = int((datetime.now() - timedelta(hours=duration_hours)).timestamp() * 1000)
            end_time = int(datetime.now().timestamp() * 1000)

            endpoint = "/stat/session"
            payload: Dict[str, Any] = {
                "type": "all",
                "start": start_time,
                "end": end_time,
                "_limit": limit,
            }
            if client_mac:
                payload["mac"] = client_mac

            api_request = ApiRequest(method="post", path=endpoint, data=payload)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error("Error getting client sessions: %s", e)
            return []

    async def get_dashboard(self) -> List[Dict[str, Any]]:
        """Get the site dashboard summary."""
        cache_key = f"{CACHE_PREFIX_STATS_DASHBOARD}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=300)  # 5 minute cache
        if cached_data is not None:
            return cached_data

        try:
            endpoint = "/stat/dashboard"
            api_request = ApiRequest(method="get", path=endpoint)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error("Error getting dashboard: %s", e)
            return []

    async def get_anomalies(self, duration_hours: int = 24) -> List[Dict[str, Any]]:
        """Get detected anomalies.

        Args:
            duration_hours: Number of hours to look back.
        """
        cache_key = f"{CACHE_PREFIX_STATS_ANOMALIES}_{duration_hours}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=300)  # 5 minute cache
        if cached_data is not None:
            return cached_data

        try:
            start_time = int((datetime.now() - timedelta(hours=duration_hours)).timestamp() * 1000)
            end_time = int(datetime.now().timestamp() * 1000)

            endpoint = "/stat/anomalies"
            payload = {
                "start": start_time,
                "end": end_time,
            }
            api_request = ApiRequest(method="post", path=endpoint, data=payload)
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error("Error getting anomalies: %s", e)
            return []

    async def get_client_wifi_details(self, client_mac: str) -> Optional[Dict[str, Any]]:
        """Get detailed WiFi information for a specific client.

        Args:
            client_mac: MAC address of the client.

        Returns:
            Dict with WiFi detail fields, or None if client not found.
        """
        cache_key = f"{CACHE_PREFIX_STATS_CLIENT_WIFI}_{client_mac}_{self._connection.site}"
        cached_data = self._connection.get_cached(cache_key, timeout=300)  # 5 minute cache
        if cached_data is not None:
            return cached_data

        try:
            endpoint = "/stat/sta"
            payload = {"mac": client_mac}
            api_request = ApiRequest(method="post", path=endpoint, data=payload)
            response = await self._connection.request(api_request)

            # Response is typically a list; find the matching client
            clients = response if isinstance(response, list) else []
            if not clients:
                return None

            # Use the first matching entry
            raw = clients[0] if isinstance(clients[0], dict) else {}

            # Extract WiFi-specific fields
            wifi_fields = [
                "signal",
                "noise",
                "satisfaction",
                "tx_rate",
                "rx_rate",
                "tx_retries",
                "wifi_tx_attempts",
                "roam_count",
                "os_name",
                "dev_vendor",
                "dev_cat",
                "dev_family",
                "channel",
                "radio",
                "essid",
                "bssid",
                "nss",
                "is_11r",
            ]
            result: Dict[str, Any] = {"mac": client_mac}
            for field in wifi_fields:
                if field in raw:
                    result[field] = raw[field]

            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error("Error getting WiFi details for client %s: %s", client_mac, e)
            return None
