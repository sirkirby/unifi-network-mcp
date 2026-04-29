"""Static DNS record serializers (Phase 4A PR1 Cluster 3).

``DnsManager`` exposes:

* ``list_dns_records()`` → ``List[Dict]``
* ``get_dns_record(record_id)`` → ``Optional[Dict]``
* ``create_dns_record(record_data)`` → ``Optional[Dict]`` (created record)
* ``update_dns_record(record_id, data)`` → ``bool``
* ``delete_dns_record(record_id)`` → ``bool``

UniFi's V2 ``/static-dns`` endpoint stores hostname under ``key`` and the
resolved value under ``value``; we surface them as ``hostname`` / ``ip`` so
the hint-shape matches caller expectations across record types.
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
        "unifi_list_dns_records": {"kind": RenderKind.LIST},
        "unifi_get_dns_record_details": {"kind": RenderKind.DETAIL},
    },
)
class DnsRecordSerializer(Serializer):
    primary_key = "id"
    display_columns = ["hostname", "type", "ip", "ttl", "enabled"]
    sort_default = "hostname:asc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "hostname": _get(obj, "key") or _get(obj, "hostname"),
            "ip": _get(obj, "value") or _get(obj, "ip"),
            "type": _get(obj, "record_type") or _get(obj, "type"),
            "ttl": _get(obj, "ttl"),
            "enabled": bool(_get(obj, "enabled", True)),
        }


@register_serializer(
    tools={
        "unifi_create_dns_record": {"kind": RenderKind.DETAIL},
        "unifi_update_dns_record": {"kind": RenderKind.DETAIL},
        "unifi_delete_dns_record": {"kind": RenderKind.DETAIL},
    },
)
class DnsMutationAckSerializer(Serializer):
    """DETAIL ack for DNS-record CUD operations.

    ``create_dns_record`` returns the created dict; ``update_*`` /
    ``delete_*`` return ``bool``. Coerce both to a DETAIL-shaped payload."""

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
