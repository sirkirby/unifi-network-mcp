"""Protect system serializers (Phase 4A PR2 Cluster 3).

Covers four NVR-level system tools:
  * ``protect_get_system_info`` — DETAIL pass-through of the bootstrap-derived
    NVR summary (``id, name, model, firmware_version, version, host, mac,
    uptime_seconds, up_since, is_updating, storage{...}, *_count``).
  * ``protect_get_health`` — DETAIL pass-through of the nested
    ``cpu/memory/storage`` health dict (plus ``is_updating``,
    ``uptime_seconds``).
  * ``protect_get_firmware_status`` — DETAIL pass-through of
    ``{nvr, devices, total_devices, devices_with_updates}``.
  * ``protect_list_viewers`` — DETAIL pass-through of the
    ``{viewers, count}`` wrapper produced by the tool layer.

The plan spec requested a different field shape (e.g. flat
``status, storage_used_pct, num_*`` for health, or ``current_version,
latest_version`` for firmware). The actual managers return richer / nested
structures, so we pass them through verbatim rather than lossily flattening.
Per the plan: "if any tool returns shape that diverges from these field
selections, adapt to actual return and document."
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _passthrough(obj: Any) -> dict:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return {"result": str(obj)}


@register_serializer(
    tools={
        "protect_get_system_info": {"kind": RenderKind.DETAIL},
    },
)
class ProtectSystemInfoSerializer(Serializer):
    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj: Any) -> dict:
        return _passthrough(obj)


@register_serializer(
    tools={
        "protect_get_health": {"kind": RenderKind.DETAIL},
    },
)
class ProtectHealthSerializer(Serializer):
    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj: Any) -> dict:
        return _passthrough(obj)


@register_serializer(
    tools={
        "protect_get_firmware_status": {"kind": RenderKind.DETAIL},
    },
)
class FirmwareStatusSerializer(Serializer):
    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj: Any) -> dict:
        return _passthrough(obj)


@register_serializer(
    tools={
        "protect_list_viewers": {"kind": RenderKind.DETAIL},
    },
)
class ViewerSerializer(Serializer):
    """Pass-through for the ``{viewers, count}`` wrapper.

    Per-viewer fields (forwarded as-is): ``id, name, type, mac, host,
    firmware_version, is_connected, is_updating, uptime_seconds, state,
    software_version, liveview_id``.
    """

    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj: Any) -> dict:
        if isinstance(obj, list):
            return {"viewers": list(obj), "count": len(obj)}
        return _passthrough(obj)
