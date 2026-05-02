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
from typing import TYPE_CHECKING, Annotated, Any

import strawberry
from strawberry.types import Info

if TYPE_CHECKING:
    from unifi_api.graphql.types.network.client import Client


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

    # Context for relationship edges — NOT in SDL, NOT in to_dict().
    _controller_id: strawberry.Private[str | None] = None
    _site: strawberry.Private[str | None] = None

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
        out = asdict(self)
        return {k: v for k, v in out.items() if not k.startswith("_") and not callable(v)}

    @strawberry.field(description="Clients on this network.")
    async def clients(
        self, info: Info,
    ) -> list[Annotated["Client", strawberry.lazy("unifi_api.graphql.types.network.client")]]:
        """Resolves to clients whose network_id matches this network's id."""
        from unifi_api.graphql.resolvers.network import _fetch_clients
        from unifi_api.graphql.types.network.client import Client

        if not self._controller_id:
            return []
        site = self._site or "default"
        raw_clients = await _fetch_clients(info.context, self._controller_id, site)
        out: list[Client] = []
        for c in raw_clients:
            if isinstance(c, dict):
                net_id = c.get("network_id")
            else:
                raw = getattr(c, "raw", None)
                net_id = (
                    raw.get("network_id") if isinstance(raw, dict)
                    else getattr(c, "network_id", None)
                )
            if net_id == self.id:
                inst = Client.from_manager_output(c)
                inst._controller_id = self._controller_id
                inst._site = site
                out.append(inst)
        return out
