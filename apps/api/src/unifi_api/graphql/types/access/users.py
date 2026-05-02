"""Strawberry types for access/users.

Phase 6 PR4 Task A migration target. The single read serializer
(``UserSerializer``) maps to one Strawberry class:

- ``User`` — access_list_users (and the ``users/{id}`` resource path,
  which is reached via list-then-filter; the access SystemManager has
  no native ``get_user`` method).

There are no user mutation tools in the access manifest today, so the
serializer module ``serializers/access/users.py`` is removed entirely
once this migration lands.

Name handling: prefer the explicit ``name`` field, otherwise stitch
``first_name`` + ``last_name`` together (mirrors the prior serializer's
``_name`` helper).
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


def _name(obj: Any) -> str | None:
    name = _get(obj, "name")
    if name:
        return name
    first = _get(obj, "first_name") or ""
    last = _get(obj, "last_name") or ""
    full = f"{first} {last}".strip()
    return full or None


@strawberry.type(description="A UniFi Access user (employee / cardholder).")
class User:
    """Mirrors ``UserSerializer.serialize`` projection byte-for-byte."""

    id: strawberry.ID | None
    name: str | None
    employee_id: str | None
    status: str | None
    role: str | None
    created_at: str | None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "employee_id", "status", "role"],
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "User":
        return cls(
            id=_get(obj, "id"),
            name=_name(obj),
            employee_id=_get(obj, "employee_id"),
            status=_get(obj, "status"),
            role=_get(obj, "role"),
            created_at=_get(obj, "created_at"),
        )

    def to_dict(self) -> dict:
        out = asdict(self)
        return {k: v for k, v in out.items() if not k.startswith("_") and not callable(v)}
