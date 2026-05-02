"""Strawberry types for protect/cameras and the camera-cluster read shapes.

Phase 6 PR3 Task A migration target. One type per read serializer that used
to live in ``unifi_api.serializers.protect.cameras``:

- ``Camera``           — protect_list_cameras + protect_get_camera
- ``CameraAnalytics``  — protect_get_camera_analytics
- ``CameraStreams``    — protect_get_camera_streams (wrapper-dict; channels +
                          rtsps_streams are passthrough JSON sub-maps keyed by
                          channel name, so we keep them as JSON scalars rather
                          than typed sub-rows)
- ``Snapshot``         — protect_get_snapshot (manager returns raw bytes;
                          surface metadata only)

Each type's ``from_manager_output(raw)`` classmethod replaces the dict-shaping
logic that used to live in serializers/protect/cameras.py. ``to_dict()``
exposes the same dict contract the REST routes return today.

Mutation ack (PTZ/reboot/toggle/update) stays in the serializer module —
those tools dispatch via the manager/preview path, not a typed read.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

import strawberry


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    raw = getattr(obj, "raw", None)
    if isinstance(raw, dict):
        return raw.get(key, default)
    return getattr(obj, key, default)


@strawberry.type(description="A UniFi Protect camera (list + detail shape).")
class Camera:
    id: strawberry.ID | None
    mac: str | None
    name: str | None
    model: str | None
    type: str | None
    state: str | None
    is_recording: bool | None
    is_motion_detected: bool | None
    is_smart_detected: bool | None
    host: str | None
    channels: strawberry.scalars.JSON | None  # type: ignore[name-defined]

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "model", "state", "is_recording"],
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "Camera":
        return cls(
            id=_get(obj, "id"),
            mac=_get(obj, "mac"),
            name=_get(obj, "name"),
            model=_get(obj, "model"),
            type=_get(obj, "type"),
            state=_get(obj, "state"),
            is_recording=_get(obj, "is_recording"),
            is_motion_detected=_get(obj, "is_motion_detected"),
            is_smart_detected=_get(obj, "is_smart_detected"),
            host=_get(obj, "ip_address") or _get(obj, "host"),
            channels=_get(obj, "channels") or [],
        )

    def to_dict(self) -> dict:
        out = asdict(self)
        return {k: v for k, v in out.items() if not k.startswith("_") and not callable(v)}


@strawberry.type(description="Analytics summary for a Protect camera.")
class CameraAnalytics:
    """Manager returns a flat-ish dict; pass through with normalised keys."""

    camera_id: strawberry.ID | None
    camera_name: str | None
    detections: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    smart_detects: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    smart_audio_detects: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    currently_detected: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    motion_zone_count: int
    smart_detect_zone_count: int
    stats: strawberry.scalars.JSON | None  # type: ignore[name-defined]

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {"kind": kind}

    @classmethod
    def from_manager_output(cls, obj: Any) -> "CameraAnalytics":
        return cls(
            camera_id=_get(obj, "camera_id"),
            camera_name=_get(obj, "camera_name"),
            detections=_get(obj, "detections") or {},
            smart_detects=_get(obj, "smart_detects") or {},
            smart_audio_detects=_get(obj, "smart_audio_detects") or {},
            currently_detected=_get(obj, "currently_detected") or {},
            motion_zone_count=_get(obj, "motion_zone_count", 0),
            smart_detect_zone_count=_get(obj, "smart_detect_zone_count", 0),
            stats=_get(obj, "stats") or {},
        )

    def to_dict(self) -> dict:
        out = asdict(self)
        return {k: v for k, v in out.items() if not k.startswith("_") and not callable(v)}


@strawberry.type(description="Stream catalog for a Protect camera (channels + RTSPS URLs).")
class CameraStreams:
    """Wrapper-dict shape: manager returns
    ``{camera_id, camera_name, channels: {name: {..}}, rtsps_streams: {...}}``.

    ``channels`` and ``rtsps_streams`` are name-keyed sub-maps with
    heterogeneous payloads; we keep them as JSON scalars rather than typed
    sub-rows because there is no stable per-channel projection in scope here.
    """

    camera_id: strawberry.ID | None
    camera_name: str | None
    channels: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    rtsps_streams: strawberry.scalars.JSON | None  # type: ignore[name-defined]

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {"kind": kind}

    @classmethod
    def from_manager_output(cls, obj: Any) -> "CameraStreams":
        return cls(
            camera_id=_get(obj, "camera_id"),
            camera_name=_get(obj, "camera_name"),
            channels=_get(obj, "channels") or {},
            rtsps_streams=_get(obj, "rtsps_streams") or {},
        )

    def to_dict(self) -> dict:
        out = asdict(self)
        return {k: v for k, v in out.items() if not k.startswith("_") and not callable(v)}


@strawberry.type(description="Metadata for a JPEG snapshot captured from a Protect camera.")
class Snapshot:
    """Manager returns raw JPEG ``bytes``; surface metadata only.

    The dict passthrough branch (when an upstream caller already produced a
    metadata dict, e.g. ``{size_bytes, content_type, captured_at, url}``)
    must mirror the original serializer to preserve the optional ``url``
    field; we represent that via a classmethod that builds different dicts
    depending on the source type and a ``to_dict()`` that strips ``None``
    keys not present on the bytes branch.
    """

    size_bytes: int | None
    content_type: str | None
    captured_at: str | None
    url: str | None = None

    # Tracks which branch produced the instance so to_dict() can re-emit the
    # exact original dict shape — bytes -> {size,content_type,captured_at};
    # dict -> {size,content_type,captured_at,url}; other -> {size:None,...}.
    _source: strawberry.Private[str] = "bytes"

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {"kind": kind}

    @classmethod
    def from_manager_output(cls, obj: Any) -> "Snapshot":
        if isinstance(obj, (bytes, bytearray)):
            inst = cls(
                size_bytes=len(obj),
                content_type="image/jpeg",
                captured_at=datetime.now(timezone.utc).isoformat(),
                url=None,
            )
            inst._source = "bytes"
            return inst
        if isinstance(obj, dict):
            inst = cls(
                size_bytes=obj.get("size_bytes"),
                content_type=obj.get("content_type", "image/jpeg"),
                captured_at=obj.get("captured_at"),
                url=obj.get("url"),
            )
            inst._source = "dict"
            return inst
        inst = cls(
            size_bytes=None,
            content_type=None,
            captured_at=None,
            url=None,
        )
        inst._source = "other"
        return inst

    def to_dict(self) -> dict:
        if self._source == "bytes":
            return {
                "size_bytes": self.size_bytes,
                "content_type": self.content_type,
                "captured_at": self.captured_at,
            }
        if self._source == "dict":
            return {
                "size_bytes": self.size_bytes,
                "content_type": self.content_type,
                "captured_at": self.captured_at,
                "url": self.url,
            }
        return {
            "size_bytes": None,
            "content_type": None,
            "captured_at": None,
        }
