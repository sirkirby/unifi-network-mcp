"""Strawberry types for network/networks (LAN/VLAN definitions).

Phase 6 PR2 Task 21 migration target. One type per read serializer that used
to live in ``unifi_api.serializers.network.networks``:

- ``Network`` — list_networks + get_network_details

Each type's ``from_manager_output(raw)`` classmethod replaces the dict-shaping
logic that used to live in serializers/network/networks.py. ``to_dict()``
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


@strawberry.type(description="A UniFi LAN/VLAN network configuration.")
class Network:
    id: strawberry.ID | None
    name: str | None
    purpose: str | None
    enabled: bool
    vlan: int | None
    subnet: str | None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "purpose", "vlan", "subnet", "enabled"],
            "sort_default": "name:asc",
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "Network":
        raw = getattr(obj, "raw", obj if isinstance(obj, dict) else {})
        return cls(
            id=raw.get("_id") or raw.get("id"),
            name=raw.get("name"),
            purpose=raw.get("purpose"),
            enabled=bool(raw.get("enabled", False)),
            vlan=raw.get("vlan"),
            subnet=raw.get("ip_subnet") or raw.get("subnet"),
        )

    def to_dict(self) -> dict:
        return asdict(self)
