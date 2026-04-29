"""Access device serializer.

``DeviceManager.list_devices`` and ``get_device`` return plain dicts.
Two paths populate slightly different shapes:

- API-client path: ``id``, ``name``, ``type``, ``connected``,
  ``firmware_version`` (and ``mac``, ``ip`` on detail).
- Proxy path: the raw topology4 device dict, which uses ``unique_id``,
  ``device_type``, ``firmware``, ``is_online`` and carries injected
  ``_door_name`` / ``_door_id`` from the topology flatten step.

We normalize across both. ``access_reboot_device`` returns a preview
dict from the manager; bool fallback for completeness.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _is_online(obj: Any) -> Any:
    explicit = _get(obj, "is_online")
    if explicit is not None:
        return explicit
    connected = _get(obj, "connected")
    if connected is not None:
        return connected
    return None


@register_serializer(
    tools={
        "access_list_devices": {"kind": RenderKind.LIST},
        "access_get_device": {"kind": RenderKind.DETAIL},
    },
)
class AccessDeviceSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "type", "is_online", "firmware_version"]
    sort_default = "name"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "id") or _get(obj, "unique_id"),
            "name": _get(obj, "name") or _get(obj, "alias"),
            "type": _get(obj, "type") or _get(obj, "device_type"),
            "is_online": _is_online(obj),
            "firmware_version": _get(obj, "firmware_version") or _get(obj, "firmware"),
            "location": _get(obj, "location") or _get(obj, "_door_name"),
        }


@register_serializer(
    tools={
        "access_reboot_device": {"kind": RenderKind.DETAIL},
    },
)
class AccessDeviceMutationAckSerializer(Serializer):
    """DETAIL ack for ``access_reboot_device``. Preview/apply both return
    dicts; pass through. Bool coerces to ``{"success": bool}``."""

    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if obj is None:
            return {"success": False}
        return {"result": str(obj)}
