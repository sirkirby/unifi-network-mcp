"""Strawberry types for protect/liveviews (Phase 6 PR3 Task C).

The single read serializer (``LiveviewSerializer``) maps to one Strawberry
class:

- ``Liveview`` — protect_list_liveviews (LIST). The manager helper
  ``_format_liveview_summary`` returns plain dicts with a ``slots`` array
  whose ``camera_ids`` we flatten into a deduped ``cameras`` list (order-
  preserving). The full ``slots`` array is preserved alongside, mirroring
  the prior serializer's projection byte-for-byte.

Mutation acks (``protect_create_liveview``, ``protect_delete_liveview``)
stay in the serializer module — those tools dispatch via the manager's
preview path. NB: both manager methods today return ``supported=False``
preview dicts since uiprotect does not expose direct create/delete APIs.
"""

from __future__ import annotations

from typing import Any, List

import strawberry


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    raw = getattr(obj, "raw", None)
    if isinstance(raw, dict):
        return raw.get(key, default)
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


@strawberry.type(description="A UniFi Protect liveview (multi-camera grid layout).")
class Liveview:
    """Mirrors ``LiveviewSerializer.serialize`` projection byte-for-byte.

    The flattened ``cameras`` list is the deduped union of slot
    camera_ids (order-preserving). The full ``slots`` payload is
    preserved as an opaque JSON sub-map since slots are heterogeneous
    (cycle_mode, cycle_interval, ...).
    """

    id: strawberry.ID | None
    name: str | None
    layout: int | None
    is_default: bool | None
    is_global: bool | None
    owner_id: str | None
    cameras: list[str]
    slots: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    slot_count: int | None
    camera_count: int | None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "layout", "camera_count"],
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "Liveview":
        slots = _get(obj, "slots") or []
        return cls(
            id=_get(obj, "id"),
            name=_get(obj, "name"),
            layout=_get(obj, "layout"),
            is_default=_get(obj, "is_default"),
            is_global=_get(obj, "is_global"),
            owner_id=_get(obj, "owner_id"),
            cameras=_flatten_cameras(slots),
            slots=slots,
            slot_count=_get(obj, "slot_count", len(slots)),
            camera_count=_get(obj, "camera_count"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "layout": self.layout,
            "is_default": self.is_default,
            "is_global": self.is_global,
            "owner_id": self.owner_id,
            "cameras": self.cameras,
            "slots": self.slots,
            "slot_count": self.slot_count,
            "camera_count": self.camera_count,
        }
