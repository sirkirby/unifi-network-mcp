"""Access schedule serializer.

``PolicyManager.list_schedules`` returns dicts from the proxy
``schedules?expand[]=week_schedule`` endpoint. Each schedule carries a
``week_schedule`` dict (per-weekday windows). We surface that as
``weekly_pattern`` for a stable catalog field name.

Only LIST is registered for this cluster — there is no detail/get tool
for schedules in Phase 4A.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


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
        "access_list_schedules": {"kind": RenderKind.LIST},
    },
)
class ScheduleSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "enabled"]
    sort_default = "name"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "id"),
            "name": _get(obj, "name"),
            "weekly_pattern": _get(obj, "weekly_pattern")
            or _get(obj, "week_schedule")
            or {},
            "enabled": _is_enabled(obj),
        }
