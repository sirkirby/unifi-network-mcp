"""Strawberry types for network/vouchers.

Phase 6 PR2 Task 23 migration target. One read shape that used to live in
``unifi_api.serializers.network.vouchers``:

- ``Voucher`` — list_vouchers + get_voucher_details
                (``/stat/voucher`` payloads from ``HotspotManager``).
                Re-emits ``create_time`` (Unix epoch) as ``created_at``,
                ``end_time`` as ``used_at`` (when ``used_at`` not present),
                matching the legacy serializer's normalization.

The mutation ack serializer (``VoucherMutationAckSerializer``) stays in the
original module for create/revoke dispatch.

Each type's ``from_manager_output(raw)`` classmethod replaces the dict-shaping
logic that used to live in serializers/network/vouchers.py.
``to_dict()`` exposes the same dict contract the REST routes return today.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import strawberry


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    raw = getattr(obj, "raw", None)
    if isinstance(raw, dict):
        return raw.get(key, default)
    return getattr(obj, key, default)


@strawberry.type(description="A hotspot voucher (V1 /stat/voucher entry).")
class Voucher:
    id: strawberry.ID | None
    code: str | None
    status: str | None
    duration: int | None
    qos_overwrite: bool
    created_at: int | None
    used_at: int | None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["code", "status", "duration", "created_at"],
            "sort_default": "created_at:desc",
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "Voucher":
        return cls(
            id=_get(obj, "_id") or _get(obj, "id"),
            code=_get(obj, "code"),
            status=_get(obj, "status"),
            duration=_get(obj, "duration"),
            qos_overwrite=bool(_get(obj, "qos_overwrite", False)),
            created_at=_get(obj, "create_time") or _get(obj, "created_at"),
            used_at=_get(obj, "used_at") or _get(obj, "end_time"),
        )

    def to_dict(self) -> dict:
        return asdict(self)
