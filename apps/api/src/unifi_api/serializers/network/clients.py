"""Network client serializers (LIST/DETAIL) plus Phase 4A Cluster 2 extensions.

The base ``ClientSerializer`` covers ``unifi_list_clients`` and
``unifi_get_client_details``. Cluster 2 adds:

* ``BlockedClientSerializer`` — LIST view for ``unifi_list_blocked_clients``.
  Manager (``ClientManager.get_blocked_clients``) returns ``List[Client]``
  (a filtered subset of all clients where ``client.blocked`` is True).
* ``ClientLookupSerializer`` — DETAIL view for ``unifi_lookup_by_ip``.
  Manager returns ``Optional[Client]`` from ``get_client_by_ip``.
* ``ClientMutationAckSerializer`` — DETAIL ack for the eight
  client-mutation tools. All underlying managers return ``bool``; coerce
  to ``{"success": bool}`` per spec section 5 EMPTY discipline.
"""

from datetime import datetime, timezone
from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


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


@register_serializer(
    tools={
        "unifi_list_clients": {"kind": RenderKind.LIST},
        "unifi_get_client_details": {"kind": RenderKind.DETAIL},
    },
    resources=[
        (("network", "clients"), {"kind": RenderKind.LIST}),
        (("network", "clients/{mac}"), {"kind": RenderKind.DETAIL}),
    ],
)
class ClientSerializer(Serializer):
    kind = RenderKind.LIST
    primary_key = "mac"
    display_columns = ["hostname", "ip", "status", "last_seen"]
    sort_default = "last_seen:desc"

    @staticmethod
    def serialize(obj) -> dict:
        raw = getattr(obj, "raw", obj if isinstance(obj, dict) else {})
        return {
            "mac": raw.get("mac"),
            "ip": raw.get("last_ip") or raw.get("ip"),
            "hostname": raw.get("hostname") or raw.get("name"),
            "is_wired": bool(raw.get("is_wired", False)),
            "is_guest": bool(raw.get("is_guest", False)),
            "status": "online" if raw.get("is_online") else "offline",
            "last_seen": _iso(raw.get("last_seen")),
            "first_seen": _iso(raw.get("first_seen")),
            "note": raw.get("note") or None,
            "usergroup_id": raw.get("usergroup_id") or None,
        }


@register_serializer(
    tools={"unifi_list_blocked_clients": {"kind": RenderKind.LIST}},
)
class BlockedClientSerializer(Serializer):
    primary_key = "mac"
    display_columns = ["mac", "hostname", "last_seen"]
    sort_default = "last_seen:desc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "mac": _get(obj, "mac"),
            "hostname": _get(obj, "hostname") or _get(obj, "name"),
            "last_seen": _iso(_get(obj, "last_seen")),
            "blocked": bool(_get(obj, "blocked", True)),
        }


@register_serializer(
    tools={"unifi_lookup_by_ip": {"kind": RenderKind.DETAIL}},
)
class ClientLookupSerializer(Serializer):
    primary_key = "mac"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "mac": _get(obj, "mac"),
            "ip": _get(obj, "last_ip") or _get(obj, "ip"),
            "hostname": _get(obj, "hostname") or _get(obj, "name"),
            "is_online": bool(_get(obj, "is_online", False)),
            "last_seen": _iso(_get(obj, "last_seen")),
        }


@register_serializer(
    tools={
        "unifi_block_client": {"kind": RenderKind.DETAIL},
        "unifi_unblock_client": {"kind": RenderKind.DETAIL},
        "unifi_forget_client": {"kind": RenderKind.DETAIL},
        "unifi_rename_client": {"kind": RenderKind.DETAIL},
        "unifi_force_reconnect_client": {"kind": RenderKind.DETAIL},
        "unifi_set_client_ip_settings": {"kind": RenderKind.DETAIL},
        "unifi_authorize_guest": {"kind": RenderKind.DETAIL},
        "unifi_unauthorize_guest": {"kind": RenderKind.DETAIL},
    },
)
class ClientMutationAckSerializer(Serializer):
    """Generic ack for client-side mutations. All underlying managers
    return ``bool`` — coerce to ``{"success": bool}``."""

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
