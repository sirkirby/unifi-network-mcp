"""Hotspot voucher serializers (Phase 4A PR1 Cluster 5).

* ``VoucherSerializer`` — ``/stat/voucher`` payloads from
  ``HotspotManager``. The controller exposes creation as ``create_time``
  (Unix epoch); we re-emit it as ``created_at`` for downstream
  consistency with other resources.
* ``VoucherMutationAckSerializer`` — DETAIL ack for create + revoke.
  ``create_voucher`` returns a list of new voucher dicts (or ``None``);
  ``revoke_voucher`` returns ``bool``.

The manifest "hotspot" category currently contains only voucher tools;
no separate non-voucher hotspot serializer is required.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    raw = getattr(obj, "raw", None)
    if isinstance(raw, dict):
        return raw.get(key, default)
    return getattr(obj, key, default)


@register_serializer(
    tools={
        "unifi_list_vouchers": {"kind": RenderKind.LIST},
        "unifi_get_voucher_details": {"kind": RenderKind.DETAIL},
    },
)
class VoucherSerializer(Serializer):
    primary_key = "id"
    display_columns = ["code", "status", "duration", "created_at"]
    sort_default = "created_at:desc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "code": _get(obj, "code"),
            "status": _get(obj, "status"),
            "duration": _get(obj, "duration"),
            "qos_overwrite": bool(_get(obj, "qos_overwrite", False)),
            "created_at": _get(obj, "create_time") or _get(obj, "created_at"),
            "used_at": _get(obj, "used_at") or _get(obj, "end_time"),
        }


@register_serializer(
    tools={
        "unifi_create_voucher": {"kind": RenderKind.DETAIL},
        "unifi_revoke_voucher": {"kind": RenderKind.DETAIL},
    },
)
class VoucherMutationAckSerializer(Serializer):
    """DETAIL ack for voucher create + revoke.

    ``create_voucher`` returns a list of new voucher dicts (or ``None``);
    ``revoke_voucher`` returns ``bool``."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, list):
            return {"success": True, "vouchers": obj}
        if isinstance(obj, dict):
            return obj
        if obj is None:
            return {"success": False}
        return {"result": str(obj)}
