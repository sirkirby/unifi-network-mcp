"""Strawberry types for network/firewall (rules + groups + zones).

Phase 6 PR2 Task 22 migration target. Three read shapes that used to live in
``unifi_api.serializers.network.firewall_rules``:

- ``FirewallRule``  — list_firewall_policies + get_firewall_policy_details
                      (also resource-keyed at ``network/firewall/rules`` and
                      ``network/firewall/rules/{id}``)
- ``FirewallGroup`` — list_firewall_groups + get_firewall_group_details
                      (V1 ``/rest/firewallgroup``; ``group_members`` is
                      re-exposed as ``members``)
- ``FirewallZone``  — list_firewall_zones (V2 zone-matrix; the manager strips
                      the policy-count matrix before this layer sees it)

The mutation ack serializer (``FirewallMutationAckSerializer``) is preserved
in the original module since it covers create/update/delete/toggle for both
firewall policies and firewall groups.

Each type's ``from_manager_output(raw)`` classmethod replaces the dict-shaping
logic that used to live in serializers/network/firewall_rules.py. ``to_dict()``
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


@strawberry.type(description="A firewall policy rule.")
class FirewallRule:
    id: strawberry.ID | None
    name: str | None
    action: str | None
    enabled: bool
    predefined: bool
    source: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    destination: strawberry.scalars.JSON | None  # type: ignore[name-defined]

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "action", "enabled", "predefined"],
            "sort_default": "name:asc",
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "FirewallRule":
        raw = getattr(obj, "raw", obj if isinstance(obj, dict) else {})
        return cls(
            id=raw.get("_id") or raw.get("id"),
            name=raw.get("name"),
            action=raw.get("action"),
            enabled=bool(raw.get("enabled", False)),
            predefined=bool(raw.get("predefined", False)),
            source=raw.get("source"),
            destination=raw.get("destination"),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@strawberry.type(description="A firewall address/port group (V1 /rest/firewallgroup).")
class FirewallGroup:
    id: strawberry.ID | None
    name: str | None
    group_type: str | None
    members: strawberry.scalars.JSON  # type: ignore[name-defined]

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "group_type", "members"],
            "sort_default": "name:asc",
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "FirewallGroup":
        members = _get(obj, "group_members") or _get(obj, "members") or []
        return cls(
            id=_get(obj, "_id") or _get(obj, "id"),
            name=_get(obj, "name"),
            group_type=_get(obj, "group_type"),
            members=members,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@strawberry.type(description="A firewall zone (V2 /firewall/zone-matrix entry).")
class FirewallZone:
    id: strawberry.ID | None
    name: str | None
    networks: strawberry.scalars.JSON  # type: ignore[name-defined]
    default_policy: str | None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "default_policy", "networks"],
            "sort_default": "name:asc",
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "FirewallZone":
        return cls(
            id=_get(obj, "_id") or _get(obj, "id"),
            name=_get(obj, "name"),
            networks=_get(obj, "networks") or _get(obj, "network_ids") or [],
            default_policy=_get(obj, "default_policy")
            or _get(obj, "default_action"),
        )

    def to_dict(self) -> dict:
        return asdict(self)
