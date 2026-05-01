"""Strawberry types for network/acl (MAC ACL rules).

Phase 6 PR2 Task 22 migration target. One read shape that used to live in
``unifi_api.serializers.network.acl``:

- ``AclRule`` — list_acl_rules + get_acl_rule_details (V2 ``/acl-rules``;
                ``GET /{id}`` returns 405, so DETAIL is served by
                list-then-filter inside the manager — both LIST and DETAIL
                receive the same shape)

The mutation ack serializer (``AclMutationAckSerializer``) stays in the
original module for create/update/delete dispatch.

The API stores source/destination match config under ``traffic_source`` /
``traffic_destination``; we surface them as ``source`` / ``destination`` to
match the firewall-rule serializer's vocabulary.

Each type's ``from_manager_output(raw)`` classmethod replaces the dict-shaping
logic that used to live in serializers/network/acl.py. ``to_dict()``
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


@strawberry.type(description="A MAC ACL rule (V2 /acl-rules entry).")
class AclRule:
    id: strawberry.ID | None
    name: str | None
    enabled: bool
    action: str | None
    source: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    destination: strawberry.scalars.JSON | None  # type: ignore[name-defined]

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "enabled", "action"],
            "sort_default": "name:asc",
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "AclRule":
        return cls(
            id=_get(obj, "_id") or _get(obj, "id"),
            name=_get(obj, "name"),
            enabled=bool(_get(obj, "enabled", False)),
            action=_get(obj, "action"),
            source=_get(obj, "traffic_source") or _get(obj, "source"),
            destination=_get(obj, "traffic_destination")
            or _get(obj, "destination"),
        )

    def to_dict(self) -> dict:
        return asdict(self)
