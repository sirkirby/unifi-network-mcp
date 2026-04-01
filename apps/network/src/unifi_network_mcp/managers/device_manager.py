import copy
import logging
from typing import Any, Dict, List, Optional

from aiounifi.models.api import ApiRequest
from aiounifi.models.device import Device

from .connection_manager import ConnectionManager

logger = logging.getLogger("unifi-network-mcp")

CACHE_PREFIX_DEVICES = "devices"
CACHE_PREFIX_ROGUE_APS = "rogue_aps"
CACHE_PREFIX_KNOWN_ROGUE_APS = "known_rogue_aps"
CACHE_PREFIX_RF_SCAN = "rf_scan"
CACHE_PREFIX_CHANNELS = "available_channels"


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
            logger.error("Error getting devices: %s", e)
            return []

    async def get_device_details(self, device_mac: str) -> Optional[Device]:
        """Get detailed information for a specific device by MAC address."""
        devices = await self.get_devices()
        device: Optional[Device] = next((d for d in devices if d.mac == device_mac), None)
        if not device:
            logger.debug("Device details for MAC %s not found in devices list.", device_mac)
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
            logger.info("Reboot command sent for device %s", device_mac)
            self._connection._invalidate_cache(CACHE_PREFIX_DEVICES)
            return True
        except Exception as e:
            logger.error("Error rebooting device %s: %s", device_mac, e)
            return False

    async def rename_device(self, device_mac: str, name: str) -> bool:
        """Rename a device."""
        try:
            device = await self.get_device_details(device_mac)
            if not device or "_id" not in device.raw:
                logger.error("Cannot rename device %s: Not found or missing ID.", device_mac)
                return False
            device_id = device.raw["_id"]

            api_request = ApiRequest(method="put", path=f"/rest/device/{device_id}", data={"name": name})
            await self._connection.request(api_request)
            logger.info("Rename command sent for device %s to '%s'", device_mac, name)
            self._connection._invalidate_cache(CACHE_PREFIX_DEVICES)
            return True
        except Exception as e:
            logger.error("Error renaming device %s to '%s': %s", device_mac, name, e)
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
            logger.info("Adopt command sent for device %s", device_mac)
            self._connection._invalidate_cache(CACHE_PREFIX_DEVICES)
            return True
        except Exception as e:
            logger.error("Error adopting device %s: %s", device_mac, e)
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
            logger.info("Upgrade command sent for device %s", device_mac)
            self._connection._invalidate_cache(CACHE_PREFIX_DEVICES)
            return True
        except Exception as e:
            logger.error("Error upgrading device %s: %s", device_mac, e)
            return False

    async def locate_device(self, device_mac: str, enabled: bool = True) -> bool:
        """Enable or disable device locate (LED blinking).

        Args:
            device_mac: MAC address of the device.
            enabled: True to start blinking, False to stop.

        Returns:
            True on success, False on failure.
        """
        try:
            cmd = "set-locate" if enabled else "unset-locate"
            api_request = ApiRequest(
                method="post",
                path="/cmd/devmgr",
                data={"cmd": cmd, "mac": device_mac},
            )
            await self._connection.request(api_request)
            logger.info("Locate %s for device %s", "enabled" if enabled else "disabled", device_mac)
            return True
        except Exception as e:
            logger.error("Error setting locate mode on device %s: %s", device_mac, e)
            return False

    async def force_provision(self, device_mac: str) -> bool:
        """Force re-provision a device.

        Args:
            device_mac: MAC address of the device.

        Returns:
            True on success, False on failure.
        """
        try:
            api_request = ApiRequest(
                method="post",
                path="/cmd/devmgr",
                data={"cmd": "force-provision", "mac": device_mac},
            )
            await self._connection.request(api_request)
            logger.info("Force provision command sent for device %s", device_mac)
            return True
        except Exception as e:
            logger.error("Error force provisioning device %s: %s", device_mac, e)
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
                logger.error("Cannot update radio for %s: device not found or missing ID.", device_mac)
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
                logger.error("Radio '%s' not found on device %s.", radio_id, device_mac)
                return False

            api_request = ApiRequest(
                method="put",
                path=f"/rest/device/{device_id}",
                data={"radio_table": radio_table},
            )
            await self._connection.request(api_request)
            logger.info("Radio '%s' updated on device %s: %s", radio_id, device_mac, list(updates.keys()))
            self._connection._invalidate_cache(CACHE_PREFIX_DEVICES)
            return True
        except Exception as e:
            logger.error("Error updating radio '%s' on device %s: %s", radio_id, device_mac, e)
            return False

    async def trigger_speedtest(self, gateway_mac: str) -> bool:
        """Trigger a speed test on the gateway.

        Args:
            gateway_mac: MAC address of the gateway device.

        Returns:
            True on success, False on failure.
        """
        try:
            api_request = ApiRequest(
                method="post",
                path="/cmd/devmgr",
                data={"mac": gateway_mac, "cmd": "speedtest"},
            )
            await self._connection.request(api_request)
            logger.info("Speedtest triggered on gateway %s", gateway_mac)
            return True
        except Exception as e:
            logger.error("Error triggering speedtest on %s: %s", gateway_mac, e)
            return False

    async def get_speedtest_status(self, gateway_mac: str) -> Dict[str, Any]:
        """Get the status of a running speed test.

        Args:
            gateway_mac: MAC address of the gateway device.

        Returns:
            Dict with speedtest status fields, or empty dict on failure.
        """
        try:
            api_request = ApiRequest(
                method="post",
                path="/cmd/devmgr",
                data={"mac": gateway_mac, "cmd": "speedtest-status"},
            )
            response = await self._connection.request(api_request)
            return response if isinstance(response, dict) else {}
        except Exception as e:
            logger.error("Error getting speedtest status for %s: %s", gateway_mac, e)
            return {}

    async def list_rogue_aps(self, within_hours: int = 24) -> List[Dict[str, Any]]:
        """List detected rogue access points.

        Args:
            within_hours: Only return rogue APs seen within this many hours.

        Returns:
            List of rogue AP dicts, or empty list on failure.
        """
        cache_key = f"{CACHE_PREFIX_ROGUE_APS}_{within_hours}_{self._connection.site}"
        cached_data: Optional[List[Dict[str, Any]]] = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            api_request = ApiRequest(
                method="post",
                path="/stat/rogueap",
                data={"within": within_hours},
            )
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error("Error listing rogue APs: %s", e)
            return []

    async def trigger_rf_scan(self, ap_mac: str) -> bool:
        """Trigger an RF spectrum scan on an access point.

        Args:
            ap_mac: MAC address of the AP to scan.

        Returns:
            True on success, False on failure.
        """
        try:
            api_request = ApiRequest(
                method="post",
                path="/cmd/devmgr",
                data={"cmd": "spectrum-scan", "mac": ap_mac},
            )
            await self._connection.request(api_request)
            logger.info("RF scan triggered on AP %s", ap_mac)
            return True
        except Exception as e:
            logger.error("Error triggering RF scan on %s: %s", ap_mac, e)
            return False

    async def get_rf_scan_results(self, ap_mac: str) -> List[Dict[str, Any]]:
        """Get RF spectrum scan results for an access point.

        Args:
            ap_mac: MAC address of the AP.

        Returns:
            List of scan result dicts, or empty list on failure.
        """
        cache_key = f"{CACHE_PREFIX_RF_SCAN}_{ap_mac}_{self._connection.site}"
        cached_data: Optional[List[Dict[str, Any]]] = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            api_request = ApiRequest(
                method="get",
                path=f"/stat/spectrum-scan/{ap_mac}",
            )
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=60)
            return result
        except Exception as e:
            logger.error("Error getting RF scan results for %s: %s", ap_mac, e)
            return []

    async def list_available_channels(self) -> List[Dict[str, Any]]:
        """List available wireless channels for the current site.

        Returns:
            List of channel info dicts, or empty list on failure.
        """
        cache_key = f"{CACHE_PREFIX_CHANNELS}_{self._connection.site}"
        cached_data: Optional[List[Dict[str, Any]]] = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            api_request = ApiRequest(
                method="get",
                path="/stat/current-channel",
            )
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=3600)
            return result
        except Exception as e:
            logger.error("Error listing available channels: %s", e)
            return []

    async def list_known_rogue_aps(self) -> List[Dict[str, Any]]:
        """List APs previously classified as known/acknowledged.

        Returns:
            List of known rogue AP dicts, or empty list on failure.
        """
        cache_key = f"{CACHE_PREFIX_KNOWN_ROGUE_APS}_{self._connection.site}"
        cached_data: Optional[List[Dict[str, Any]]] = self._connection.get_cached(cache_key)
        if cached_data is not None:
            return cached_data

        try:
            api_request = ApiRequest(
                method="get",
                path="/rest/rogueknown",
            )
            response = await self._connection.request(api_request)
            result = response if isinstance(response, list) else []
            self._connection._update_cache(cache_key, result, timeout=300)
            return result
        except Exception as e:
            logger.error("Error listing known rogue APs: %s", e)
            return []

    async def set_device_led_override(self, device_mac: str, led_override: str) -> bool:
        """Set LED override state on a device.

        Args:
            device_mac: MAC address of the device.
            led_override: LED state - "on", "off", or "default".

        Returns:
            True on success, False on failure.
        """
        try:
            device = await self.get_device_details(device_mac)
            if not device or "_id" not in device.raw:
                logger.error("Cannot set LED override for %s: Not found or missing ID.", device_mac)
                return False
            device_id = device.raw["_id"]

            api_request = ApiRequest(
                method="put",
                path=f"/rest/device/{device_id}",
                data={"led_override": led_override},
            )
            await self._connection.request(api_request)
            logger.info("LED override set to '%s' for device %s", led_override, device_mac)
            self._connection._invalidate_cache(CACHE_PREFIX_DEVICES)
            return True
        except Exception as e:
            logger.error("Error setting LED override on device %s: %s", device_mac, e)
            return False

    async def set_device_disabled(self, device_mac: str, disabled: bool) -> bool:
        """Enable or disable a device without unadopting it.

        Args:
            device_mac: MAC address of the device.
            disabled: True to disable, False to enable.

        Returns:
            True on success, False on failure.
        """
        try:
            device = await self.get_device_details(device_mac)
            if not device or "_id" not in device.raw:
                logger.error("Cannot set disabled state for %s: Not found or missing ID.", device_mac)
                return False
            device_id = device.raw["_id"]

            api_request = ApiRequest(
                method="put",
                path=f"/rest/device/{device_id}",
                data={"disabled": disabled},
            )
            await self._connection.request(api_request)
            logger.info("Device %s %s", device_mac, "disabled" if disabled else "enabled")
            self._connection._invalidate_cache(CACHE_PREFIX_DEVICES)
            return True
        except Exception as e:
            logger.error("Error setting disabled state on device %s: %s", device_mac, e)
            return False

    async def set_site_led_enabled(self, enabled: bool) -> bool:
        """Toggle all device LEDs site-wide.

        Args:
            enabled: True to enable LEDs, False to disable.

        Returns:
            True on success, False on failure.
        """
        try:
            api_request = ApiRequest(
                method="put",
                path="/set/setting/mgmt",
                data={"led_enabled": enabled},
            )
            await self._connection.request(api_request)
            logger.info("Site LEDs %s", "enabled" if enabled else "disabled")
            return True
        except Exception as e:
            logger.error("Error setting site LED state: %s", e)
            return False
