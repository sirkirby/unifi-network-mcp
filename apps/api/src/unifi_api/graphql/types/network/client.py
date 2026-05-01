"""Strawberry types for network/clients.

Canonical migration target for Phase 6 PR2:
- ``Client``        — list_clients + get_client_details (full client shape)
- ``BlockedClient`` — list_blocked_clients (minimal blocked-list shape)
- ``ClientLookup``  — lookup_by_ip (online-status check shape)

Each type's ``from_manager_output(raw)`` classmethod replaces the dict-shaping
logic that used to live in serializers/network/clients.py. ``to_dict()``
exposes the same dict contract the REST routes return today.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

import strawberry


def _iso(ts: int | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    raw = getattr(obj, "raw", None)
    if isinstance(raw, dict):
        return raw.get(key, default)
    return getattr(obj, key, default)


@strawberry.type(description="A client device on the UniFi Network controller.")
class Client:
    mac: strawberry.ID | None
    ip: str | None
    hostname: str | None
    is_wired: bool
    is_guest: bool
    status: str
    last_seen: str | None
    first_seen: str | None
    note: str | None
    usergroup_id: str | None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "mac",
            "display_columns": ["hostname", "ip", "status", "last_seen"],
            "sort_default": "last_seen:desc",
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "Client":
        raw = getattr(obj, "raw", obj if isinstance(obj, dict) else {})
        return cls(
            mac=raw.get("mac"),
            ip=raw.get("last_ip") or raw.get("ip"),
            hostname=raw.get("hostname") or raw.get("name"),
            is_wired=bool(raw.get("is_wired", False)),
            is_guest=bool(raw.get("is_guest", False)),
            status="online" if raw.get("is_online") else "offline",
            last_seen=_iso(raw.get("last_seen")),
            first_seen=_iso(raw.get("first_seen")),
            note=raw.get("note") or None,
            usergroup_id=raw.get("usergroup_id") or None,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@strawberry.type(description="A client currently blocked on the UniFi Network controller.")
class BlockedClient:
    mac: strawberry.ID | None
    hostname: str | None
    last_seen: str | None
    blocked: bool

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "mac",
            "display_columns": ["mac", "hostname", "last_seen"],
            "sort_default": "last_seen:desc",
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "BlockedClient":
        return cls(
            mac=_get(obj, "mac"),
            hostname=_get(obj, "hostname") or _get(obj, "name"),
            last_seen=_iso(_get(obj, "last_seen")),
            blocked=bool(_get(obj, "blocked", True)),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@strawberry.type(description="Result of a by-IP client lookup — online presence + last seen.")
class ClientLookup:
    mac: strawberry.ID | None
    ip: str | None
    hostname: str | None
    is_online: bool
    last_seen: str | None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {"kind": kind, "primary_key": "mac"}

    @classmethod
    def from_manager_output(cls, obj: Any) -> "ClientLookup":
        return cls(
            mac=_get(obj, "mac"),
            ip=_get(obj, "last_ip") or _get(obj, "ip"),
            hostname=_get(obj, "hostname") or _get(obj, "name"),
            is_online=bool(_get(obj, "is_online", False)),
            last_seen=_iso(_get(obj, "last_seen")),
        )

    def to_dict(self) -> dict:
        return asdict(self)
