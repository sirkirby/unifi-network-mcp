"""Access policy serializer.

``PolicyManager.list_policies`` and ``get_policy`` return dicts from the
proxy ``access_policies?expand[]=schedule`` endpoint. Policies expose
schedule and door associations under various field names depending on
expansion (``resources``, ``door_ids``, ``schedule_id``). We normalize
to a stable shape for catalog use.

``access_update_policy`` returns a preview dict (current_state +
proposed_changes); the apply path returns ``{"result": "success", ...}``.
``PolicyMutationAckSerializer`` passes both through and coerces bools.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _door_ids(obj: Any) -> list:
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


def _is_enabled(obj: Any) -> bool:
    explicit = _get(obj, "enabled")
    if isinstance(explicit, bool):
        return explicit
    status = _get(obj, "status")
    if isinstance(status, str):
        return status.lower() in {"active", "enabled", "on"}
    return True


@register_serializer(
    tools={
        "access_list_policies": {"kind": RenderKind.LIST},
        "access_get_policy": {"kind": RenderKind.DETAIL},
    },
)
class PolicySerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "schedule_id", "enabled"]
    sort_default = "name"

    @staticmethod
    def serialize(obj) -> dict:
        schedule = _get(obj, "schedule")
        schedule_id = _get(obj, "schedule_id")
        if not schedule_id and isinstance(schedule, dict):
            schedule_id = schedule.get("id")
        return {
            "id": _get(obj, "id"),
            "name": _get(obj, "name"),
            "schedule_id": schedule_id,
            "door_ids": _door_ids(obj),
            "user_group_ids": _get(obj, "user_group_ids") or [],
            "enabled": _is_enabled(obj),
        }


@register_serializer(
    tools={
        "access_update_policy": {"kind": RenderKind.DETAIL},
    },
)
class PolicyMutationAckSerializer(Serializer):
    """DETAIL ack for ``access_update_policy``. Preview/apply both return
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
