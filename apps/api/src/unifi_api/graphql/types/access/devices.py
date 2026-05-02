"""Strawberry types for access/devices.

Phase 6 PR4 Task A migration target. The single read serializer
(``AccessDeviceSerializer``) maps to one Strawberry class:

- ``AccessDevice`` — access_list_devices + access_get_device

DeviceManager populates two slightly different shapes (API-client path vs
proxy path with topology4 ``unique_id`` / ``device_type`` / ``firmware``
and injected ``_door_name`` / ``_door_id``); ``from_manager_output``
normalizes across both, mirroring the old serializer byte-for-byte.

Mutation ack (``access_reboot_device``) stays in the serializer module —
that tool dispatches via the manager's preview path, not a typed read.
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


def _is_online(obj: Any) -> Any:
    explicit = _get(obj, "is_online")
    if explicit is not None:
        return explicit
    connected = _get(obj, "connected")
    if connected is not None:
        return connected
    return None


@strawberry.type(description="A UniFi Access device (reader / hub / lock).")
class AccessDevice:
    """Mirrors ``AccessDeviceSerializer.serialize`` projection byte-for-byte."""

    id: strawberry.ID | None
    name: str | None
    type: str | None
    is_online: bool | None
    firmware_version: str | None
    location: str | None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "type", "is_online", "firmware_version"],
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "AccessDevice":
        return cls(
            id=_get(obj, "id") or _get(obj, "unique_id"),
            name=_get(obj, "name") or _get(obj, "alias"),
            type=_get(obj, "type") or _get(obj, "device_type"),
            is_online=_is_online(obj),
            firmware_version=_get(obj, "firmware_version") or _get(obj, "firmware"),
            location=_get(obj, "location") or _get(obj, "_door_name"),
        )

    def to_dict(self) -> dict:
        out = asdict(self)
        return {k: v for k, v in out.items() if not k.startswith("_") and not callable(v)}
