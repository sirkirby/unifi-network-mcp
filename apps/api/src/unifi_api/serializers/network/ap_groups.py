"""AP group serializers (Phase 4A PR1 Cluster 3).

AP groups live on V2 ``/apgroups`` and ride on ``NetworkManager`` (not a
dedicated manager). Methods:

* ``list_ap_groups()`` → ``List[Dict]``
* ``get_ap_group_details(group_id)`` → ``Optional[Dict]`` (V2 ``GET /{id}``
  returns 405; manager fetches all and filters)
* ``create_ap_group(group_data)`` → ``Optional[Dict]``
* ``update_ap_group(group_id, data)`` → ``bool``
* ``delete_ap_group(group_id)`` → ``bool``
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
        "unifi_list_ap_groups": {"kind": RenderKind.LIST},
        "unifi_get_ap_group_details": {"kind": RenderKind.DETAIL},
    },
)
class ApGroupSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "ap_count"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        device_macs = _get(obj, "device_macs") or []
        if not isinstance(device_macs, list):
            device_macs = []
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "ap_count": len(device_macs),
            "device_macs": list(device_macs),
        }


@register_serializer(
    tools={
        "unifi_create_ap_group": {"kind": RenderKind.DETAIL},
        "unifi_update_ap_group": {"kind": RenderKind.DETAIL},
        "unifi_delete_ap_group": {"kind": RenderKind.DETAIL},
    },
)
class ApGroupMutationAckSerializer(Serializer):
    """DETAIL ack for AP group CUD operations.

    ``create_ap_group`` returns the created dict; ``update_*``/``delete_*``
    return ``bool``."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, dict):
            return obj
        raw = getattr(obj, "raw", None)
        if isinstance(raw, dict):
            return raw
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        return {"result": str(obj)}
