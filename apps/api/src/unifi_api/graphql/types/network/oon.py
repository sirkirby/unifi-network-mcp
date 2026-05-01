"""Strawberry types for network/oon (out-of-network policies).

Phase 6 PR2 Task 22 migration target. One read shape that used to live in
``unifi_api.serializers.network.oon``:

- ``OonPolicy`` — list_oon_policies + get_oon_policy_details

OON policies bundle ``targets`` (a list of ``{type, value}`` matchers
covering MACs, group IDs, etc.) plus a ``secure`` config (with nested
``internet`` mode), a ``qos`` slice, and a ``route`` slice. The LIST render
surfaces only name/enabled and the target list (re-exposed as ``applies_to``);
``restriction_level`` is a controller-side label that the manager passes
through unchanged when present — newer firmware exposes it; older firmware
leaves it out.

The mutation ack serializer (``OonMutationAckSerializer``) stays in the
original module for create/update/delete/toggle dispatch.

Each type's ``from_manager_output(raw)`` classmethod replaces the dict-shaping
logic that used to live in serializers/network/oon.py. ``to_dict()``
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


@strawberry.type(description="An out-of-network (OON) policy entry.")
class OonPolicy:
    id: strawberry.ID | None
    name: str | None
    enabled: bool
    applies_to: strawberry.scalars.JSON  # type: ignore[name-defined]
    restriction_level: str | None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "enabled", "restriction_level"],
            "sort_default": "name:asc",
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "OonPolicy":
        return cls(
            id=_get(obj, "_id") or _get(obj, "id"),
            name=_get(obj, "name"),
            enabled=bool(_get(obj, "enabled", False)),
            applies_to=_get(obj, "targets") or _get(obj, "applies_to") or [],
            restriction_level=_get(obj, "restriction_level"),
        )

    def to_dict(self) -> dict:
        return asdict(self)
