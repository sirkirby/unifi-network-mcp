"""Strawberry types for network/wlans (WLAN/SSID definitions).

Phase 6 PR2 Task 21 migration target. One type per read serializer that used
to live in ``unifi_api.serializers.network.wlans``:

- ``Wlan`` — list_wlans + get_wlan_details

Each type's ``from_manager_output(raw)`` classmethod replaces the dict-shaping
logic that used to live in serializers/network/wlans.py. ``to_dict()``
exposes the same dict contract the REST routes return today.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import strawberry


@strawberry.type(description="A UniFi WLAN/SSID configuration.")
class Wlan:
    id: strawberry.ID | None
    name: str | None
    enabled: bool
    security: str | None
    network_id: str | None
    hide_ssid: bool
    vlan_id: int | None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "security", "enabled", "vlan_id"],
            "sort_default": "name:asc",
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "Wlan":
        raw = getattr(obj, "raw", obj if isinstance(obj, dict) else {})
        return cls(
            id=raw.get("_id") or raw.get("id"),
            name=raw.get("name"),
            enabled=bool(raw.get("enabled", False)),
            security=raw.get("security"),
            network_id=raw.get("networkconf_id") or raw.get("network_id"),
            hide_ssid=bool(raw.get("hide_ssid", False)),
            vlan_id=raw.get("vlan") or raw.get("vlan_id"),
        )

    def to_dict(self) -> dict:
        return asdict(self)
