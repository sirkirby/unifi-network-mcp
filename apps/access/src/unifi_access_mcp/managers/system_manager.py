"""System management for UniFi Access.

Provides methods to query Access system information, health,
and user listings from the Access controller.  Each method
tries the API client first (if available) and falls back to
the proxy session path.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from unifi_access_mcp.managers.connection_manager import AccessConnectionManager
from unifi_core.exceptions import UniFiConnectionError

logger = logging.getLogger(__name__)


class SystemManager:
    """Reads system-level data from the Access controller."""

    def __init__(self, connection_manager: AccessConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    async def get_system_info(self) -> Dict[str, Any]:
        """Return Access controller model, version, uptime, and overview.

        Uses the API client ``get_doors`` as a connectivity probe when
        available; falls back to the proxy ``system/info`` endpoint.
        """
        if self._cm.has_api_client:
            try:
                # py-unifi-access does not expose a dedicated system-info
                # endpoint, but we can use get_doors() as a health probe
                # and report basic connectivity information.
                doors = await self._cm.api_client.get_doors()
                return {
                    "source": "api_client",
                    "host": self._cm.host,
                    "api_port": self._cm._api_port,
                    "connected": True,
                    "door_count": len(doors),
                }
            except Exception as exc:
                logger.warning(
                    "[system] API client system info failed, falling back to proxy: %s",
                    exc,
                )

        if self._cm.has_proxy:
            try:
                data = await self._cm.proxy_request("GET", "system/info")
                return data.get("data", data) if isinstance(data, dict) else data
            except Exception as exc:
                logger.error("[system] Failed to get system info via proxy: %s", exc, exc_info=True)
                raise

        raise UniFiConnectionError("No auth path available for get_system_info")

    async def get_health(self) -> Dict[str, Any]:
        """Return system health summary.

        Checks both auth paths and reports their individual status.
        """
        health: Dict[str, Any] = {
            "host": self._cm.host,
            "is_connected": self._cm.is_connected,
            "api_client_available": self._cm.has_api_client,
            "proxy_available": self._cm.has_proxy,
        }

        # Probe API client path
        if self._cm.has_api_client:
            try:
                await self._cm.api_client.get_doors()
                health["api_client_healthy"] = True
            except Exception as exc:
                logger.warning("[system] API client health probe failed: %s", exc)
                health["api_client_healthy"] = False
                health["api_client_error"] = str(exc)

        # Probe proxy path
        if self._cm.has_proxy:
            try:
                await self._cm.proxy_request("GET", "system/health")
                health["proxy_healthy"] = True
            except Exception as exc:
                logger.warning("[system] Proxy health probe failed: %s", exc)
                health["proxy_healthy"] = False
                health["proxy_error"] = str(exc)

        return health

    async def list_users(self) -> list[Dict[str, Any]]:
        """List users with access.

        Uses the proxy path ``/proxy/access/api/v2/users`` since the
        ``py-unifi-access`` library does not expose a user listing endpoint.
        """
        if self._cm.has_proxy:
            try:
                data = await self._cm.proxy_request("GET", "users")
                if isinstance(data, dict):
                    return data.get("data", [data])
                if isinstance(data, list):
                    return data
                return [data]
            except Exception as exc:
                logger.error("[system] Failed to list users via proxy: %s", exc, exc_info=True)
                raise

        raise UniFiConnectionError("No auth path available for list_users (proxy session required)")
