import logging
from typing import Dict, List, Optional, Any

from aiounifi.models.api import ApiRequest
from aiounifi.models.device import Device
from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_DEVICES = "devices"

class DeviceManager:
    """Manages device-related operations on the Unifi Controller."""

    def __init__(self, connection_manager: ConnectionManager):
        """Initialize the Device Manager.

        Args:
            connection_manager: The shared ConnectionManager instance.
        """
        self._connection = connection_manager

    async def get_devices(self) -> List[Device]:
        """Get list of devices for the current site."""
        if not await self._connection.ensure_connected() or not self._connection.controller:
            return []

        cache_key = f"{CACHE_PREFIX_DEVICES}_{self._connection.site}"
        cached_data: Optional[List[Device]] = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            await self._connection.controller.devices.update()
            devices: List[Device] = list(self._connection.controller.devices.values())
            self._connection._update_cache(cache_key, devices)
            return devices
        except Exception as e:
            logger.error(f"Error getting devices: {e}")
            return []

    async def get_device_details(self, device_mac: str) -> Optional[Device]:
        """Get detailed information for a specific device by MAC address."""
        devices = await self.get_devices()
        device: Optional[Device] = next((d for d in devices if d.mac == device_mac), None)
        if not device:
             logger.debug(f"Device details for MAC {device_mac} not found in devices list.")
        return device

    async def reboot_device(self, device_mac: str) -> bool:
        """Reboot a device by MAC address."""
        try:
            api_request = ApiRequest(
                method="post",
                path=f"/cmd/devmgr",
                json={"mac": device_mac, "cmd": "restart"}
            )
            await self._connection.request(api_request)
            logger.info(f"Reboot command sent for device {device_mac}")
            self._connection._invalidate_cache(CACHE_PREFIX_DEVICES)
            return True
        except Exception as e:
            logger.error(f"Error rebooting device {device_mac}: {e}")
            return False

    async def rename_device(self, device_mac: str, name: str) -> bool:
        """Rename a device."""
        try:
            device = await self.get_device_details(device_mac)
            if not device or "_id" not in device.raw:
                logger.error(f"Cannot rename device {device_mac}: Not found or missing ID.")
                return False
            device_id = device.raw["_id"]

            api_request = ApiRequest(
                method="put",
                path=f"/rest/device/{device_id}",
                json={"name": name}
            )
            await self._connection.request(api_request)
            logger.info(f"Rename command sent for device {device_mac} to '{name}'")
            self._connection._invalidate_cache(CACHE_PREFIX_DEVICES)
            return True
        except Exception as e:
            logger.error(f"Error renaming device {device_mac} to '{name}': {e}")
            return False

    async def adopt_device(self, device_mac: str) -> bool:
        """Adopt a device by MAC address."""
        try:
            api_request = ApiRequest(
                method="post",
                path="/cmd/devmgr",
                json={"mac": device_mac, "cmd": "adopt"}
            )
            await self._connection.request(api_request)
            logger.info(f"Adopt command sent for device {device_mac}")
            self._connection._invalidate_cache(CACHE_PREFIX_DEVICES)
            return True
        except Exception as e:
            logger.error(f"Error adopting device {device_mac}: {e}")
            return False

    async def upgrade_device(self, device_mac: str) -> bool:
        """Start firmware upgrade for a device by MAC address."""
        try:
            api_request = ApiRequest(
                method="post",
                path="/cmd/devmgr",
                json={"mac": device_mac, "cmd": "upgrade"}
            )
            await self._connection.request(api_request)
            logger.info(f"Upgrade command sent for device {device_mac}")
            self._connection._invalidate_cache(CACHE_PREFIX_DEVICES)
            return True
        except Exception as e:
            logger.error(f"Error upgrading device {device_mac}: {e}")
            return False 