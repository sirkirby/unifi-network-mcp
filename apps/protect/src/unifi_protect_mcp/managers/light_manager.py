"""Light management for UniFi Protect.

Provides methods to list and update UniFi Protect floodlight devices
via the uiprotect bootstrap data.

Key API surface on ``Light``:
- ``set_light(enabled, led_level=None)`` -- turn on/off, optionally set level
- ``set_led_level(level)`` -- set LED brightness (1-6)
- ``set_sensitivity(sensitivity)`` -- set PIR motion sensitivity (0-100)
- ``set_duration(duration)`` -- set motion-triggered on duration (timedelta)
- ``set_light_settings(mode, enable_at, duration, sensitivity)`` -- bulk update
- ``set_status_light(enabled)`` -- toggle the status indicator LED
- ``set_name(name)`` -- rename the device
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List

from unifi_protect_mcp.managers.connection_manager import ProtectConnectionManager

logger = logging.getLogger(__name__)


class LightManager:
    """Domain logic for UniFi Protect lights (floodlights)."""

    def __init__(self, connection_manager: ProtectConnectionManager) -> None:
        self._cm = connection_manager

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_light(self, light_id: str):
        """Retrieve a Light object by ID, raising ValueError if not found."""
        lights = self._cm.client.bootstrap.lights
        light = lights.get(light_id)
        if light is None:
            raise ValueError(f"Light not found: {light_id}")
        return light

    @staticmethod
    def _format_light_summary(light) -> Dict[str, Any]:
        """Format a light into a summary dict with essential fields."""
        # Light device settings
        device_settings: Dict[str, Any] = {}
        if light.light_device_settings:
            ds = light.light_device_settings
            device_settings = {
                "is_indicator_enabled": ds.is_indicator_enabled,
                "led_level": ds.led_level,
                "pir_duration_seconds": int(ds.pir_duration.total_seconds()) if ds.pir_duration else None,
                "pir_sensitivity": ds.pir_sensitivity,
            }

        # Light on settings
        light_on = {}
        if light.light_on_settings:
            light_on = {
                "is_led_force_on": light.light_on_settings.is_led_force_on,
            }

        # Light mode settings
        mode_settings: Dict[str, Any] = {}
        if light.light_mode_settings:
            ms = light.light_mode_settings
            mode_settings = {
                "mode": str(ms.mode.value) if ms.mode else None,
                "enable_at": str(ms.enable_at.value) if ms.enable_at else None,
            }

        return {
            "id": light.id,
            "name": light.name,
            "type": str(light.type),
            "model": light.market_name or str(light.type),
            "state": str(light.state.value) if light.state else None,
            "is_connected": light.is_connected,
            "firmware_version": light.firmware_version,
            "last_seen": light.last_seen.isoformat() if light.last_seen else None,
            "is_light_on": light.is_light_on,
            "is_dark": light.is_dark,
            "is_pir_motion_detected": light.is_pir_motion_detected,
            "last_motion": light.last_motion.isoformat() if light.last_motion else None,
            "camera_id": light.camera_id,
            "is_camera_paired": light.is_camera_paired,
            "device_settings": device_settings,
            "light_on_settings": light_on,
            "mode_settings": mode_settings,
        }

    # ------------------------------------------------------------------
    # Read-only methods
    # ------------------------------------------------------------------

    async def list_lights(self) -> List[Dict[str, Any]]:
        """Return all lights as summary dicts."""
        lights = self._cm.client.bootstrap.lights
        return [self._format_light_summary(light) for light in lights.values()]

    # ------------------------------------------------------------------
    # Mutation methods (preview / apply)
    # ------------------------------------------------------------------

    async def update_light(self, light_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Return current and proposed light state for preview.

        Supported settings keys:
        - light_on: bool -- turn light on/off
        - led_level: int (1-6) -- LED brightness level
        - sensitivity: int (0-100) -- PIR motion sensitivity
        - duration_seconds: int (15-900) -- motion-triggered on duration
        - status_light: bool -- status indicator LED
        - name: str -- device name
        """
        light = self._get_light(light_id)

        current_state: Dict[str, Any] = {}
        proposed_changes: Dict[str, Any] = {}

        for key, value in settings.items():
            if key == "light_on":
                current_state["light_on"] = light.is_light_on
                proposed_changes["light_on"] = value
            elif key == "led_level":
                current_led = light.light_device_settings.led_level if light.light_device_settings else None
                current_state["led_level"] = current_led
                proposed_changes["led_level"] = value
            elif key == "sensitivity":
                current_sens = light.light_device_settings.pir_sensitivity if light.light_device_settings else None
                current_state["sensitivity"] = current_sens
                proposed_changes["sensitivity"] = value
            elif key == "duration_seconds":
                current_dur = None
                if light.light_device_settings and light.light_device_settings.pir_duration:
                    current_dur = int(light.light_device_settings.pir_duration.total_seconds())
                current_state["duration_seconds"] = current_dur
                proposed_changes["duration_seconds"] = value
            elif key == "status_light":
                current_state["status_light"] = (
                    light.light_device_settings.is_indicator_enabled if light.light_device_settings else None
                )
                proposed_changes["status_light"] = value
            elif key == "name":
                current_state["name"] = light.name
                proposed_changes["name"] = value
            else:
                logger.warning("Unknown light setting key: %s", key)

        return {
            "light_id": light_id,
            "light_name": light.name,
            "current_state": current_state,
            "proposed_changes": proposed_changes,
        }

    async def apply_light_settings(self, light_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Apply light settings after confirmation."""
        light = self._get_light(light_id)
        applied: List[str] = []
        errors: List[str] = []

        for key, value in settings.items():
            try:
                if key == "light_on":
                    await light.set_light(bool(value))
                    applied.append(f"light_on={value}")
                elif key == "led_level":
                    await light.set_led_level(int(value))
                    applied.append(f"led_level={value}")
                elif key == "sensitivity":
                    await light.set_sensitivity(int(value))
                    applied.append(f"sensitivity={value}")
                elif key == "duration_seconds":
                    await light.set_duration(timedelta(seconds=int(value)))
                    applied.append(f"duration_seconds={value}")
                elif key == "status_light":
                    await light.set_status_light(bool(value))
                    applied.append(f"status_light={value}")
                elif key == "name":
                    await light.set_name(str(value))
                    applied.append(f"name={value}")
                else:
                    errors.append(f"Unknown setting: {key}")
            except Exception as exc:
                logger.error("Error applying light setting %s=%s: %s", key, value, exc, exc_info=True)
                errors.append(f"{key}: {exc}")

        result: Dict[str, Any] = {
            "light_id": light_id,
            "light_name": light.name,
            "applied": applied,
        }
        if errors:
            result["errors"] = errors

        return result
