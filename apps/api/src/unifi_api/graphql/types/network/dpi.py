"""Strawberry types for network/dpi (DPI applications + categories).

Phase 6 PR2 Task 22 migration target. Two read shapes that used to live in
``unifi_api.serializers.network.dpi``:

- ``DpiApplication`` — list_dpi_applications (V2 official integration API)
- ``DpiCategory``    — list_dpi_categories

DPI is a read-only resource — no create/update/delete tools exist, so no
mutation ack serializer is needed. The original module empties out
completely after migration.

Critical detail: DPI ids can be 0 (e.g. category 0 = "Instant messengers");
the ``ident or fallback`` pattern collapses 0 → None. The
``from_manager_output`` here mirrors the legacy serializer's explicit
``is None`` check to preserve the 0 value.

Each type's ``from_manager_output(raw)`` classmethod replaces the dict-shaping
logic that used to live in serializers/network/dpi.py. ``to_dict()``
exposes the same dict contract the REST routes return today.
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


@strawberry.type(description="A DPI application classification entry.")
class DpiApplication:
    id: int | None
    name: str | None
    category_id: int | None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "category_id"],
            "sort_default": "name:asc",
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "DpiApplication":
        # DPI ids can be 0 (e.g. category 0 = Instant messengers); avoid the
        # ``a or b`` pattern that collapses 0 → None.
        ident = _get(obj, "id")
        if ident is None:
            ident = _get(obj, "_id")
        cat = _get(obj, "categoryId")
        if cat is None:
            cat = _get(obj, "category_id")
        return cls(
            id=ident,
            name=_get(obj, "name"),
            category_id=cat,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@strawberry.type(description="A DPI application category.")
class DpiCategory:
    id: int | None
    name: str | None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name"],
            "sort_default": "name:asc",
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "DpiCategory":
        ident = _get(obj, "id")
        if ident is None:
            ident = _get(obj, "_id")
        return cls(
            id=ident,
            name=_get(obj, "name"),
        )

    def to_dict(self) -> dict:
        return asdict(self)
