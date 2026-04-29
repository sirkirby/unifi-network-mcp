"""Protect sensor serializer.

``SensorManager.list_sensors`` returns plain dicts shaped by
``_format_sensor_summary``. Battery / humidity / light statuses are
nested under ``battery`` and ``stats`` so we flatten them here.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _nested_status(obj: Any, parent_key: str, child_key: str = "status") -> Any:
    parent = _get(obj, parent_key) or {}
    if isinstance(parent, dict):
        return parent.get(child_key)
    return getattr(parent, child_key, None)


@register_serializer(
    tools={
        "protect_list_sensors": {"kind": RenderKind.LIST},
    },
    resources=[
        (("protect", "sensors"), {"kind": RenderKind.LIST}),
    ],
)
class SensorSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "type", "battery_status", "motion_detected_at"]

    @staticmethod
    def serialize(obj) -> dict:
        stats = _get(obj, "stats") or {}
        humidity = stats.get("humidity") if isinstance(stats, dict) else getattr(stats, "humidity", None)
        light = stats.get("light") if isinstance(stats, dict) else getattr(stats, "light", None)
        return {
            "id": _get(obj, "id"),
            "mac": _get(obj, "mac"),
            "name": _get(obj, "name"),
            "type": _get(obj, "type"),
            "battery_status": _nested_status(obj, "battery"),
            "humidity_status": humidity.get("status") if isinstance(humidity, dict) else None,
            "light_status": light.get("status") if isinstance(light, dict) else None,
            "motion_detected_at": _get(obj, "motion_detected_at"),
        }
