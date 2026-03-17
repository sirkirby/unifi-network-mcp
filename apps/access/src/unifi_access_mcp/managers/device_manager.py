"""Device management for UniFi Access.

Provides methods to query and manage Access hardware devices (hubs, readers,
relays, intercoms) via the Access controller API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from unifi_access_mcp.managers.connection_manager import AccessConnectionManager

logger = logging.getLogger(__name__)


class DeviceManager:
    """Reads and mutates device data from the Access controller."""

    def __init__(self, connection_manager: AccessConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Read-only methods (stubs)
    # ------------------------------------------------------------------

    async def list_devices(self) -> List[Dict[str, Any]]:
        """Return all Access devices as summary dicts."""
        raise NotImplementedError("DeviceManager.list_devices not yet implemented")

    async def get_device(self, device_id: str) -> Dict[str, Any]:
        """Return detailed information for a single device."""
        raise NotImplementedError("DeviceManager.get_device not yet implemented")

    # ------------------------------------------------------------------
    # Mutation methods (stubs)
    # ------------------------------------------------------------------

    async def restart_device(self, device_id: str) -> Dict[str, Any]:
        """Restart a device. Returns preview data."""
        raise NotImplementedError("DeviceManager.restart_device not yet implemented")
