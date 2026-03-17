"""Sensor management for UniFi Protect.

Provides methods to list UniFi Protect sensor devices (motion, door/window,
temperature, humidity, light level, leak detection) via the uiprotect
bootstrap data.

Sensors are read-only hardware devices -- they report environmental data
but have no user-controllable settings exposed through the public API.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from unifi_protect_mcp.managers.connection_manager import ProtectConnectionManager

logger = logging.getLogger(__name__)


class SensorManager:
    """Domain logic for UniFi Protect sensors."""

    def __init__(self, connection_manager: ProtectConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_sensor_summary(sensor) -> Dict[str, Any]:
        """Format a sensor into a summary dict with essential fields."""
        # Battery status
        battery: Dict[str, Any] = {}
        if sensor.battery_status:
            battery = {
                "percentage": sensor.battery_status.percentage,
                "is_low": sensor.battery_status.is_low,
            }

        # Stats (light, humidity, temperature readings)
        stats: Dict[str, Any] = {}
        if sensor.stats:
            for stat_name in ("light", "humidity", "temperature"):
                stat = getattr(sensor.stats, stat_name, None)
                if stat:
                    stats[stat_name] = {
                        "value": stat.value,
                        "status": str(stat.status.value) if stat.status else None,
                    }

        return {
            "id": sensor.id,
            "name": sensor.name,
            "type": str(sensor.type),
            "model": sensor.market_name or str(sensor.type),
            "state": str(sensor.state.value) if sensor.state else None,
            "is_connected": sensor.is_connected,
            "firmware_version": sensor.firmware_version,
            "last_seen": sensor.last_seen.isoformat() if sensor.last_seen else None,
            "mount_type": str(sensor.mount_type.value) if sensor.mount_type else None,
            "is_motion_detected": sensor.is_motion_detected,
            "is_opened": sensor.is_opened,
            "motion_detected_at": (sensor.motion_detected_at.isoformat() if sensor.motion_detected_at else None),
            "open_status_changed_at": (
                sensor.open_status_changed_at.isoformat() if sensor.open_status_changed_at else None
            ),
            "alarm_triggered_at": (sensor.alarm_triggered_at.isoformat() if sensor.alarm_triggered_at else None),
            "leak_detected_at": (sensor.leak_detected_at.isoformat() if sensor.leak_detected_at else None),
            "tampering_detected_at": (
                sensor.tampering_detected_at.isoformat() if sensor.tampering_detected_at else None
            ),
            "battery": battery,
            "stats": stats,
            "camera_id": sensor.camera_id,
        }

    # ------------------------------------------------------------------
    # Read-only methods
    # ------------------------------------------------------------------

    async def list_sensors(self) -> List[Dict[str, Any]]:
        """Return all sensors as summary dicts."""
        sensors = self._cm.client.bootstrap.sensors
        return [self._format_sensor_summary(sensor) for sensor in sensors.values()]
