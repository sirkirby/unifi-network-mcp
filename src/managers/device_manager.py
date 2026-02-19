import copy
import logging
from typing import Any, Dict, List, Optional

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
                path="/cmd/devmgr",
                data={"mac": device_mac, "cmd": "restart"},
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

            api_request = ApiRequest(method="put", path=f"/rest/device/{device_id}", data={"name": name})
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
                data={"mac": device_mac, "cmd": "adopt"},
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
                data={"mac": device_mac, "cmd": "upgrade"},
            )
            await self._connection.request(api_request)
            logger.info(f"Upgrade command sent for device {device_mac}")
            self._connection._invalidate_cache(CACHE_PREFIX_DEVICES)
            return True
        except Exception as e:
            logger.error(f"Error upgrading device {device_mac}: {e}")
            return False

    async def get_device_radio(self, device_mac: str) -> Optional[Dict[str, Any]]:
        """Get focused radio configuration and live stats for an AP.

        Returns None if device is not found or is not an access point.
        """
        device = await self.get_device_details(device_mac)
        if not device:
            return None
        device_type = device.raw.get("type", "")
        if not device_type.startswith("uap"):
            return None

        stats_by_name: Dict[str, Dict[str, Any]] = {s["name"]: s for s in device.raw.get("radio_table_stats", [])}
        radios: List[Dict[str, Any]] = []
        for radio in device.raw.get("radio_table", []):
            entry: Dict[str, Any] = {
                "name": radio.get("name"),
                "radio": radio.get("radio"),
                "channel": radio.get("channel"),
                "ht": radio.get("ht"),
                "tx_power_mode": radio.get("tx_power_mode"),
                "tx_power": radio.get("tx_power"),
                "min_rssi_enabled": radio.get("min_rssi_enabled"),
                "min_rssi": radio.get("min_rssi"),
                "max_txpower": radio.get("max_txpower"),
                "min_txpower": radio.get("min_txpower"),
                "has_dfs": radio.get("has_dfs"),
                "nss": radio.get("nss"),
                "is_11ax": radio.get("is_11ax", False),
                "is_11be": radio.get("is_11be", False),
            }
            if stats := stats_by_name.get(radio.get("name", "")):
                entry["current_tx_power"] = stats.get("tx_power")
                entry["current_channel"] = stats.get("channel")
                entry["cu_total"] = stats.get("cu_total")
                entry["cu_self_tx"] = stats.get("cu_self_tx")
                entry["cu_self_rx"] = stats.get("cu_self_rx")
                entry["satisfaction"] = stats.get("satisfaction")
                entry["num_sta"] = stats.get("num_sta")
                entry["tx_retries"] = stats.get("tx_retries")
                entry["tx_packets"] = stats.get("tx_packets")
            radios.append(entry)

        return {
            "mac": device_mac,
            "name": device.raw.get("name", device.raw.get("model", "Unknown")),
            "model": device.raw.get("model", ""),
            "radios": radios,
        }

    async def update_device_radio(self, device_mac: str, radio_id: str, updates: Dict[str, Any]) -> bool:
        """Update radio settings for a specific band on an AP.

        Args:
            device_mac: MAC address of the AP.
            radio_id: Radio identifier -- either the band code ("na", "ng", "6e")
                      or the internal name ("wifi0", "wifi1").
            updates: Dict of radio_table fields to update (e.g. tx_power_mode, channel).

        Returns:
            True on success, False on failure.
        """
        try:
            device = await self.get_device_details(device_mac)
            if not device or "_id" not in device.raw:
                logger.error(f"Cannot update radio for {device_mac}: device not found or missing ID.")
                return False
            device_id = device.raw["_id"]

            radio_table = copy.deepcopy(device.raw.get("radio_table", []))
            matched = False
            for entry in radio_table:
                if entry.get("radio") == radio_id or entry.get("name") == radio_id:
                    entry.update(updates)
                    matched = True
                    break

            if not matched:
                logger.error(f"Radio '{radio_id}' not found on device {device_mac}.")
                return False

            api_request = ApiRequest(
                method="put",
                path=f"/rest/device/{device_id}",
                data={"radio_table": radio_table},
            )
            await self._connection.request(api_request)
            logger.info(f"Radio '{radio_id}' updated on device {device_mac}: {list(updates.keys())}")
            self._connection._invalidate_cache(CACHE_PREFIX_DEVICES)
            return True
        except Exception as e:
            logger.error(f"Error updating radio '{radio_id}' on device {device_mac}: {e}")
            return False
