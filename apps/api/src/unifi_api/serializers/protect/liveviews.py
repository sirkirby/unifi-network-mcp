"""Protect liveview serializers (Phase 4A PR2 Cluster 2).

``LiveviewManager.list_liveviews`` returns plain dicts shaped by
``_format_liveview_summary``. Each entry has::

    {id, name, is_default, is_global, layout, owner_id,
     slots: [{camera_ids, cycle_mode, cycle_interval}], slot_count, camera_count}

For the LIST view we flatten ``slots`` into a deduped ``cameras`` list of
camera IDs (preserving order) — that's what consumers actually want for a
liveview at a glance. The full ``slots`` array is preserved alongside.

Mutation acks cover ``protect_create_liveview`` / ``protect_delete_liveview``.
NB: both manager methods today return ``supported=False`` preview dicts since
uiprotect does not expose direct create/delete APIs.
"""

from typing import Any, List

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _flatten_cameras(slots: list) -> List[str]:
    seen: set = set()
    out: List[str] = []
    for slot in slots or []:
        cam_ids = _get(slot, "camera_ids") or []
        for cid in cam_ids:
            if cid not in seen:
                seen.add(cid)
                out.append(cid)
    return out


@register_serializer(
    tools={
        "protect_list_liveviews": {"kind": RenderKind.LIST},
    },
    resources=[
        (("protect", "liveviews"), {"kind": RenderKind.LIST}),
    ],
)
class LiveviewSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "id"
    display_columns = ["name", "layout", "camera_count"]

    @staticmethod
    def serialize(obj) -> dict:
        slots = _get(obj, "slots") or []
        return {
            "id": _get(obj, "id"),
            "name": _get(obj, "name"),
            "layout": _get(obj, "layout"),
            "is_default": _get(obj, "is_default"),
            "is_global": _get(obj, "is_global"),
            "owner_id": _get(obj, "owner_id"),
            "cameras": _flatten_cameras(slots),
            "slots": slots,
            "slot_count": _get(obj, "slot_count", len(slots)),
            "camera_count": _get(obj, "camera_count"),
        }


@register_serializer(
    tools={
        "protect_create_liveview": {"kind": RenderKind.DETAIL},
        "protect_delete_liveview": {"kind": RenderKind.DETAIL},
    },
)
class LiveviewMutationAckSerializer(Serializer):
    """Pass-through for liveview create/delete preview dicts. Bool fallback."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
