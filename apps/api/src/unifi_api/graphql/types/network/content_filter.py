"""Strawberry types for network/content_filter.

Phase 6 PR2 Task 22 migration target. One read shape that used to live in
``unifi_api.serializers.network.content_filter``:

- ``ContentFilter`` — list_content_filters + get_content_filter_details
                      (V2 ``/content-filtering``; ``GET /{id}`` returns 405,
                      so DETAIL is served by list-then-filter inside the
                      manager — both LIST and DETAIL receive the same shape)

The mutation ack serializer (``ContentFilterMutationAckSerializer``) stays
in the original module for update + delete dispatch (no create — UniFi ships
a fixed set of profiles).

Each type's ``from_manager_output(raw)`` classmethod replaces the dict-shaping
logic that used to live in serializers/network/content_filter.py.
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


@strawberry.type(description="A content-filtering profile (V2 /content-filtering entry).")
class ContentFilter:
    id: strawberry.ID | None
    name: str | None
    enabled: bool
    profile: str | None
    applies_to: strawberry.scalars.JSON  # type: ignore[name-defined]

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "enabled", "profile"],
            "sort_default": "name:asc",
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "ContentFilter":
        return cls(
            id=_get(obj, "_id") or _get(obj, "id"),
            name=_get(obj, "name"),
            enabled=bool(_get(obj, "enabled", False)),
            profile=_get(obj, "profile"),
            applies_to=_get(obj, "applies_to") or _get(obj, "network_ids") or [],
        )

    def to_dict(self) -> dict:
        return asdict(self)
