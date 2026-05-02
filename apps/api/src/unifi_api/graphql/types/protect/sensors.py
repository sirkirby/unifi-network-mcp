"""Strawberry types for protect/sensors (Phase 6 PR3 Task C).

The single read serializer (``SensorSerializer``) maps to one Strawberry
class:

- ``Sensor`` — protect_list_sensors (LIST). Battery / humidity / light
  statuses are flattened from nested ``battery`` / ``stats`` sub-maps in
  the manager dict, matching the prior serializer's projection
  byte-for-byte.

There is no mutation serializer for sensors today (the manager exposes
no preview-and-confirm flows for sensor settings).
"""

from __future__ import annotations

from typing import Any

import strawberry


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    raw = getattr(obj, "raw", None)
    if isinstance(raw, dict):
        return raw.get(key, default)
    return getattr(obj, key, default)


def _nested_status(obj: Any, parent_key: str, child_key: str = "status") -> Any:
    parent = _get(obj, parent_key) or {}
    if isinstance(parent, dict):
        return parent.get(child_key)
    return getattr(parent, child_key, None)


@strawberry.type(description="A UniFi Protect sensor (motion / leak / temperature).")
class Sensor:
    """Mirrors ``SensorSerializer.serialize`` projection byte-for-byte."""

    id: strawberry.ID | None
    mac: str | None
    name: str | None
    type: str | None
    battery_status: str | None
    humidity_status: str | None
    light_status: str | None
    motion_detected_at: str | None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "type", "battery_status", "motion_detected_at"],
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "Sensor":
        stats = _get(obj, "stats") or {}
        if isinstance(stats, dict):
            humidity = stats.get("humidity")
            light = stats.get("light")
        else:
            humidity = getattr(stats, "humidity", None)
            light = getattr(stats, "light", None)
        return cls(
            id=_get(obj, "id"),
            mac=_get(obj, "mac"),
            name=_get(obj, "name"),
            type=_get(obj, "type"),
            battery_status=_nested_status(obj, "battery"),
            humidity_status=humidity.get("status") if isinstance(humidity, dict) else None,
            light_status=light.get("status") if isinstance(light, dict) else None,
            motion_detected_at=_get(obj, "motion_detected_at"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mac": self.mac,
            "name": self.name,
            "type": self.type,
            "battery_status": self.battery_status,
            "humidity_status": self.humidity_status,
            "light_status": self.light_status,
            "motion_detected_at": self.motion_detected_at,
        }
