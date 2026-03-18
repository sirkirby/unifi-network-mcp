"""Device management for UniFi Access.

Provides methods to query and manage Access hardware devices (hubs, readers,
relays, intercoms) via the Access controller API.

Dual-path routing: tries the API client (py-unifi-access) first when
available, then falls back to the proxy session path.

Proxy paths discovered via browser inspection:
- ``devices/topology4`` -- device topology (full device tree)
- ``protect_devices?include_adopted_by_access=true`` -- Protect devices paired with Access
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from unifi_access_mcp.managers.connection_manager import AccessConnectionManager
from unifi_core.exceptions import UniFiConnectionError

logger = logging.getLogger(__name__)


class DeviceManager:
    """Reads and mutates device data from the Access controller."""

    def __init__(self, connection_manager: AccessConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Read-only methods
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_devices_from_topology(topology: Any) -> List[Dict[str, Any]]:
        """Flatten the nested topology4 structure into a device list.

        The topology4 response has the structure::

            [site] -> floors -> doors -> device_groups -> [devices]

        Each device uses ``unique_id`` as its identifier.
        """
        devices: List[Dict[str, Any]] = []
        sites = topology if isinstance(topology, list) else [topology] if isinstance(topology, dict) else []
        for site in sites:
            if not isinstance(site, dict):
                continue
            for floor in site.get("floors", []):
                if not isinstance(floor, dict):
                    continue
                for door in floor.get("doors", []):
                    if not isinstance(door, dict):
                        continue
                    for dg in door.get("device_groups", []):
                        # device_groups can be a list of lists or list of dicts
                        group_devices = (
                            dg if isinstance(dg, list) else dg.get("devices", []) if isinstance(dg, dict) else []
                        )
                        for dev in group_devices:
                            if isinstance(dev, dict):
                                dev["_door_name"] = door.get("name")
                                dev["_door_id"] = door.get("unique_id")
                                devices.append(dev)
        return devices

    async def list_devices(self) -> List[Dict[str, Any]]:
        """Return all Access devices as summary dicts.

        Tries the API client first, then falls back to the proxy path
        using the ``devices/topology4`` endpoint.
        """
        try:
            if self._cm.has_api_client:
                devices = await self._cm.api_client.get_devices()
                return [
                    {
                        "id": getattr(d, "id", None),
                        "name": getattr(d, "name", None),
                        "type": getattr(d, "type", None),
                        "connected": getattr(d, "connected", None),
                        "firmware_version": getattr(d, "firmware_version", None),
                    }
                    for d in devices
                ]
            elif self._cm.has_proxy:
                data = await self._cm.proxy_request("GET", "devices/topology4")
                topology = self._cm.extract_data(data)
                return self._extract_devices_from_topology(topology)
            else:
                raise UniFiConnectionError("No auth path available for list_devices")
        except UniFiConnectionError:
            raise
        except Exception as e:
            logger.error("Failed to list devices: %s", e, exc_info=True)
            raise

    async def get_device(self, device_id: str) -> Dict[str, Any]:
        """Return detailed information for a single device.

        Tries the API client first, then falls back to the proxy path.
        When using the proxy path we flatten the topology tree and search
        by ``unique_id`` or ``mac``.
        """
        if not device_id:
            raise ValueError("device_id is required")
        try:
            if self._cm.has_api_client:
                device = await self._cm.api_client.get_device(device_id)
                return {
                    "id": getattr(device, "id", None),
                    "name": getattr(device, "name", None),
                    "type": getattr(device, "type", None),
                    "connected": getattr(device, "connected", None),
                    "firmware_version": getattr(device, "firmware_version", None),
                    "mac": getattr(device, "mac", None),
                    "ip": getattr(device, "ip", None),
                }
            elif self._cm.has_proxy:
                data = await self._cm.proxy_request("GET", "devices/topology4")
                topology = self._cm.extract_data(data)
                devices = self._extract_devices_from_topology(topology)
                for dev in devices:
                    if dev.get("unique_id") == device_id or dev.get("mac") == device_id:
                        return dev
                raise ValueError(f"Device not found: {device_id}")
            else:
                raise UniFiConnectionError("No auth path available for get_device")
        except (UniFiConnectionError, ValueError):
            raise
        except Exception as e:
            logger.error("Failed to get device %s: %s", device_id, e, exc_info=True)
            raise

    # ------------------------------------------------------------------
    # Mutation methods (preview/confirm pattern)
    # ------------------------------------------------------------------

    async def reboot_device(self, device_id: str) -> Dict[str, Any]:
        """Preview a device reboot. Returns preview data for confirmation."""
        if not device_id:
            raise ValueError("device_id is required")

        current = await self.get_device(device_id)
        return {
            "device_id": device_id,
            "device_name": current.get("name"),
            "device_type": current.get("type"),
            "current_state": {
                "connected": current.get("connected"),
                "firmware_version": current.get("firmware_version"),
            },
            "proposed_changes": {
                "action": "reboot",
            },
        }

    async def apply_reboot_device(self, device_id: str) -> Dict[str, Any]:
        """Execute the device reboot on the controller.

        Uses the proxy path since device reboot is not exposed by the
        py-unifi-access API client.
        """
        try:
            if self._cm.has_proxy:
                await self._cm.proxy_request("POST", f"devices/{device_id}/reboot")
                return {
                    "device_id": device_id,
                    "action": "reboot",
                    "result": "success",
                }
            else:
                raise UniFiConnectionError("No proxy session available for reboot_device")
        except UniFiConnectionError:
            raise
        except Exception as e:
            logger.error("Failed to reboot device %s: %s", device_id, e, exc_info=True)
            raise
