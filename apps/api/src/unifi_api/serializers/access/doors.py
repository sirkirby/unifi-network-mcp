"""Access door serializer.

``DoorManager.list_doors`` / ``get_door`` return plain dicts. Two paths
populate slightly different shapes:

- API-client path: ``id``, ``name``, ``door_position_status``,
  ``lock_relay_status`` (and ``camera_resource_id``, ``door_guard`` on
  detail).
- Proxy path: the raw location dict, which keeps richer fields like
  ``location_type``, ``devices``, ``is_online``, ``last_event``.

We normalize across both. ``is_locked`` is derived from
``lock_relay_status`` when present (``"lock"``); otherwise we honor an
explicit ``is_locked`` key on the dict.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _is_locked(obj: Any) -> bool | None:
    explicit = _get(obj, "is_locked")
    if explicit is not None:
        return bool(explicit)
    relay = _get(obj, "lock_relay_status")
    if relay is None:
        return None
    return relay == "lock"


def _last_event(obj: Any) -> Any:
    raw = _get(obj, "last_event")
    if isinstance(raw, dict):
        return {
            "name": raw.get("name"),
            "timestamp": raw.get("timestamp") or raw.get("created_at"),
        }
    return raw


@register_serializer(
    tools={
        "access_list_doors": {"kind": RenderKind.LIST},
        "access_get_door": {"kind": RenderKind.DETAIL},
    },
    resources=[
        (("access", "doors"), {"kind": RenderKind.LIST}),
        (("access", "doors/{id}"), {"kind": RenderKind.DETAIL}),
    ],
)
class DoorSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "location", "is_online", "is_locked"]
    sort_default = "name"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "id"),
            "name": _get(obj, "name"),
            "location": _get(obj, "location") or _get(obj, "location_type"),
            "is_online": _get(obj, "is_online"),
            "is_locked": _is_locked(obj),
            "lock_state": _get(obj, "lock_state") or _get(obj, "lock_relay_status"),
            "last_event": _last_event(obj),
        }


def _door_ids_from_groups(obj: Any) -> list:
    """Door groups may carry resources/door_ids in either field name."""
    door_ids = _get(obj, "door_ids")
    if isinstance(door_ids, list):
        return door_ids
    resources = _get(obj, "resources")
    if isinstance(resources, list):
        return [
            r.get("id") if isinstance(r, dict) else r
            for r in resources
            if r is not None
        ]
    return []


@register_serializer(
    tools={
        "access_list_door_groups": {"kind": RenderKind.LIST},
    },
)
class DoorGroupSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "location"]
    sort_default = "name"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "id"),
            "name": _get(obj, "name"),
            "door_ids": _door_ids_from_groups(obj),
            "location": _get(obj, "location") or _get(obj, "location_type"),
        }


@register_serializer(
    tools={
        "access_get_door_status": {"kind": RenderKind.DETAIL},
    },
)
class DoorStatusSerializer(Serializer):
    kind = RenderKind.DETAIL
    primary_key = "door_id"

    @staticmethod
    def serialize(obj) -> dict:
        last = _last_event(obj)
        last_ts = last.get("timestamp") if isinstance(last, dict) else None
        last_type = last.get("name") if isinstance(last, dict) else None
        return {
            "door_id": _get(obj, "door_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "is_locked": _is_locked(obj),
            "lock_state": _get(obj, "lock_state") or _get(obj, "lock_relay_status"),
            "door_position_status": _get(obj, "door_position_status"),
            "last_event_at": last_ts,
            "last_event_type": last_type,
        }


@register_serializer(
    tools={
        "access_lock_door": {"kind": RenderKind.DETAIL},
        "access_unlock_door": {"kind": RenderKind.DETAIL},
    },
)
class DoorMutationAckSerializer(Serializer):
    """DETAIL ack for lock/unlock. Manager preview returns a dict
    (door_id + current_state + proposed_changes); pass through. Bool
    coerces to ``{"success": bool}`` for completeness."""

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
