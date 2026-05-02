"""Strawberry types for protect/system (Phase 6 PR3 Task C).

Four read serializers move here from
``unifi_api.serializers.protect.system``, all pass-through wrappers since
the manager / tool layer hands richer / nested structures than any flat
field selection could capture without lossy flattening:

- ``ProtectSystemInfo`` — protect_get_system_info (DETAIL flat
  pass-through). NVR-level summary
  (``id, name, model, firmware_version, version, host, mac,
  uptime_seconds, up_since, is_updating, storage{...}, *_count``).
- ``ProtectHealth`` — protect_get_health (DETAIL flat pass-through).
  Nested ``cpu/memory/storage`` health dict (plus ``is_updating``,
  ``uptime_seconds``).
- ``FirmwareStatus`` — protect_get_firmware_status (DETAIL pass-through
  of ``{nvr, devices, total_devices, devices_with_updates}``).
- ``ViewerList`` — protect_list_viewers (DETAIL wrapper-dict
  pass-through of the ``{viewers, count}`` shape produced by the tool
  layer; bare list also coerced into the wrapper).

Each type carries a ``_raw`` private payload so ``to_dict`` returns the
exact dict shape the original serializer emitted (including any extra
keys the manager surfaces beyond the typed field selection).
"""

from __future__ import annotations

from typing import Any

import strawberry


@strawberry.type(description="UniFi Protect NVR-level system info (pass-through).")
class ProtectSystemInfo:
    """DETAIL pass-through for the system_info dict.

    Surfaces a representative subset of fields as typed; the original
    payload is preserved verbatim via ``to_dict`` so wider manager
    responses round-trip byte-for-byte.
    """

    id: strawberry.ID | None
    name: str | None
    model: str | None
    firmware_version: str | None
    version: str | None
    host: str | None
    mac: str | None
    uptime_seconds: int | None
    up_since: str | None
    is_updating: bool | None
    storage: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    camera_count: int | None
    light_count: int | None
    sensor_count: int | None
    viewer_count: int | None
    chime_count: int | None

    _raw: strawberry.Private[dict[str, Any] | None] = None
    _fallback: strawberry.Private[str | None] = None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {"kind": kind}

    @classmethod
    def from_manager_output(cls, obj: Any) -> "ProtectSystemInfo":
        if isinstance(obj, dict):
            inst = cls(
                id=obj.get("id"),
                name=obj.get("name"),
                model=obj.get("model"),
                firmware_version=obj.get("firmware_version"),
                version=obj.get("version"),
                host=obj.get("host"),
                mac=obj.get("mac"),
                uptime_seconds=obj.get("uptime_seconds"),
                up_since=obj.get("up_since"),
                is_updating=obj.get("is_updating"),
                storage=obj.get("storage"),
                camera_count=obj.get("camera_count"),
                light_count=obj.get("light_count"),
                sensor_count=obj.get("sensor_count"),
                viewer_count=obj.get("viewer_count"),
                chime_count=obj.get("chime_count"),
            )
            inst._raw = dict(obj)
            return inst
        if hasattr(obj, "model_dump"):
            dumped = obj.model_dump()
            inst = cls(
                id=dumped.get("id"),
                name=dumped.get("name"),
                model=dumped.get("model"),
                firmware_version=dumped.get("firmware_version"),
                version=dumped.get("version"),
                host=dumped.get("host"),
                mac=dumped.get("mac"),
                uptime_seconds=dumped.get("uptime_seconds"),
                up_since=dumped.get("up_since"),
                is_updating=dumped.get("is_updating"),
                storage=dumped.get("storage"),
                camera_count=dumped.get("camera_count"),
                light_count=dumped.get("light_count"),
                sensor_count=dumped.get("sensor_count"),
                viewer_count=dumped.get("viewer_count"),
                chime_count=dumped.get("chime_count"),
            )
            inst._raw = dict(dumped)
            return inst
        inst = cls(
            id=None,
            name=None,
            model=None,
            firmware_version=None,
            version=None,
            host=None,
            mac=None,
            uptime_seconds=None,
            up_since=None,
            is_updating=None,
            storage=None,
            camera_count=None,
            light_count=None,
            sensor_count=None,
            viewer_count=None,
            chime_count=None,
        )
        inst._fallback = str(obj)
        return inst

    def to_dict(self) -> dict:
        if self._raw is not None:
            return self._raw
        if self._fallback is not None:
            return {"result": self._fallback}
        return {}


@strawberry.type(description="UniFi Protect NVR health snapshot (pass-through).")
class ProtectHealth:
    """DETAIL pass-through for the health dict.

    The nested ``cpu/memory/storage`` sub-maps are surfaced as JSON
    payloads to preserve the manager's structure verbatim.
    """

    cpu: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    memory: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    storage: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    is_updating: bool | None
    uptime_seconds: int | None

    _raw: strawberry.Private[dict[str, Any] | None] = None
    _fallback: strawberry.Private[str | None] = None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {"kind": kind}

    @classmethod
    def from_manager_output(cls, obj: Any) -> "ProtectHealth":
        if isinstance(obj, dict):
            inst = cls(
                cpu=obj.get("cpu"),
                memory=obj.get("memory"),
                storage=obj.get("storage"),
                is_updating=obj.get("is_updating"),
                uptime_seconds=obj.get("uptime_seconds"),
            )
            inst._raw = dict(obj)
            return inst
        if hasattr(obj, "model_dump"):
            dumped = obj.model_dump()
            inst = cls(
                cpu=dumped.get("cpu"),
                memory=dumped.get("memory"),
                storage=dumped.get("storage"),
                is_updating=dumped.get("is_updating"),
                uptime_seconds=dumped.get("uptime_seconds"),
            )
            inst._raw = dict(dumped)
            return inst
        inst = cls(
            cpu=None,
            memory=None,
            storage=None,
            is_updating=None,
            uptime_seconds=None,
        )
        inst._fallback = str(obj)
        return inst

    def to_dict(self) -> dict:
        if self._raw is not None:
            return self._raw
        if self._fallback is not None:
            return {"result": self._fallback}
        return {}


@strawberry.type(description="Firmware status for the NVR plus its devices.")
class FirmwareStatus:
    """DETAIL pass-through for the firmware-status dict.

    Mirrors ``{nvr, devices, total_devices, devices_with_updates}``;
    sub-dicts kept opaque since the manager's per-device entries are
    heterogeneous.
    """

    nvr: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    devices: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    total_devices: int | None
    devices_with_updates: int | None

    _raw: strawberry.Private[dict[str, Any] | None] = None
    _fallback: strawberry.Private[str | None] = None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {"kind": kind}

    @classmethod
    def from_manager_output(cls, obj: Any) -> "FirmwareStatus":
        if isinstance(obj, dict):
            inst = cls(
                nvr=obj.get("nvr"),
                devices=obj.get("devices"),
                total_devices=obj.get("total_devices"),
                devices_with_updates=obj.get("devices_with_updates"),
            )
            inst._raw = dict(obj)
            return inst
        if hasattr(obj, "model_dump"):
            dumped = obj.model_dump()
            inst = cls(
                nvr=dumped.get("nvr"),
                devices=dumped.get("devices"),
                total_devices=dumped.get("total_devices"),
                devices_with_updates=dumped.get("devices_with_updates"),
            )
            inst._raw = dict(dumped)
            return inst
        inst = cls(
            nvr=None,
            devices=None,
            total_devices=None,
            devices_with_updates=None,
        )
        inst._fallback = str(obj)
        return inst

    def to_dict(self) -> dict:
        if self._raw is not None:
            return self._raw
        if self._fallback is not None:
            return {"result": self._fallback}
        return {}


@strawberry.type(description="A UniFi Protect viewer (Viewport).")
class Viewer:
    """Sub-row for a single viewer — used by the per-page REST projection.

    Pass-through: manager helper returns a flat dict per viewer
    (``id, name, type, mac, host, firmware_version, is_connected,
    is_updating, uptime_seconds, state, software_version, liveview_id``).
    """

    id: strawberry.ID | None
    name: str | None
    type: str | None
    mac: str | None
    host: str | None
    firmware_version: str | None
    is_connected: bool | None
    is_updating: bool | None
    uptime_seconds: int | None
    state: str | None
    software_version: str | None
    liveview_id: str | None

    _raw: strawberry.Private[dict[str, Any] | None] = None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {
            "kind": kind,
            "primary_key": "id",
            "display_columns": ["name", "state", "is_connected", "liveview_id"],
        }

    @classmethod
    def from_manager_output(cls, obj: Any) -> "Viewer":
        if isinstance(obj, dict):
            inst = cls(
                id=obj.get("id"),
                name=obj.get("name"),
                type=obj.get("type"),
                mac=obj.get("mac"),
                host=obj.get("host"),
                firmware_version=obj.get("firmware_version"),
                is_connected=obj.get("is_connected"),
                is_updating=obj.get("is_updating"),
                uptime_seconds=obj.get("uptime_seconds"),
                state=obj.get("state"),
                software_version=obj.get("software_version"),
                liveview_id=obj.get("liveview_id"),
            )
            inst._raw = dict(obj)
            return inst
        if hasattr(obj, "model_dump"):
            dumped = obj.model_dump()
            inst = cls(
                id=dumped.get("id"),
                name=dumped.get("name"),
                type=dumped.get("type"),
                mac=dumped.get("mac"),
                host=dumped.get("host"),
                firmware_version=dumped.get("firmware_version"),
                is_connected=dumped.get("is_connected"),
                is_updating=dumped.get("is_updating"),
                uptime_seconds=dumped.get("uptime_seconds"),
                state=dumped.get("state"),
                software_version=dumped.get("software_version"),
                liveview_id=dumped.get("liveview_id"),
            )
            inst._raw = dict(dumped)
            return inst
        inst = cls(
            id=None,
            name=None,
            type=None,
            mac=None,
            host=None,
            firmware_version=None,
            is_connected=None,
            is_updating=None,
            uptime_seconds=None,
            state=None,
            software_version=None,
            liveview_id=None,
        )
        return inst

    def to_dict(self) -> dict:
        if self._raw is not None:
            return self._raw
        return {}


@strawberry.type(description="Wrapper for protect_list_viewers — {viewers, count}.")
class ViewerList:
    """Wrapper-dict pass-through for ``{viewers: [...], count}``.

    Mirrors ``ViewerSerializer.serialize`` exactly: dict identity,
    bare-list coercion to ``{viewers, count: len}``, ``model_dump`` for
    pydantic, ``{"result": str(obj)}`` fallback. Used by the action
    endpoint where the whole response is the wrapper. The REST list
    route projects per-viewer via ``Viewer`` directly when needed.
    """

    viewers: strawberry.scalars.JSON | None  # type: ignore[name-defined]
    count: int | None

    _raw: strawberry.Private[dict[str, Any] | None] = None
    _fallback: strawberry.Private[str | None] = None

    @classmethod
    def render_hint(cls, kind: str) -> dict:
        return {"kind": kind}

    @classmethod
    def from_manager_output(cls, obj: Any) -> "ViewerList":
        if isinstance(obj, dict):
            inst = cls(
                viewers=obj.get("viewers") or [],
                count=obj.get("count"),
            )
            inst._raw = dict(obj)
            return inst
        if isinstance(obj, list):
            wrapper = {"viewers": list(obj), "count": len(obj)}
            inst = cls(viewers=wrapper["viewers"], count=wrapper["count"])
            inst._raw = wrapper
            return inst
        if hasattr(obj, "model_dump"):
            dumped = obj.model_dump()
            inst = cls(
                viewers=dumped.get("viewers") or [],
                count=dumped.get("count"),
            )
            inst._raw = dict(dumped)
            return inst
        inst = cls(viewers=None, count=None)
        inst._fallback = str(obj)
        return inst

    def to_dict(self) -> dict:
        if self._raw is not None:
            return self._raw
        if self._fallback is not None:
            return {"result": self._fallback}
        return {}
