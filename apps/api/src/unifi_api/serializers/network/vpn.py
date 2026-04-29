"""VPN serializers (Phase 4A PR1 Cluster 3).

VPN configurations live inside the ``networkconf`` API and are filtered by
purpose / vpn_type. ``VpnManager`` returns:

* ``get_vpn_clients()`` / ``get_vpn_servers()`` → ``List[Dict]``
* ``get_vpn_client_details()`` / ``get_vpn_server_details()`` → ``Optional[Dict]``
* ``update_vpn_client_state()`` / ``update_vpn_server_state()`` → ``bool``

The common fields surfaced here mirror the manager output without
re-classifying — we expose ``vpn_type`` directly as ``type`` so callers can
disambiguate wireguard vs openvpn vs l2tp.
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


def _vpn_server_address(obj: Any) -> str | None:
    # Wireguard client peer endpoint, openvpn remote, or generic server.
    return (
        _get(obj, "wireguard_client_peer_endpoint")
        or _get(obj, "openvpn_remote_host")
        or _get(obj, "remote_address")
        or _get(obj, "server_address")
    )


def _vpn_listen_port(obj: Any) -> int | None:
    return (
        _get(obj, "wireguard_server_listen_port")
        or _get(obj, "openvpn_server_listen_port")
        or _get(obj, "vpn_listen_port")
        or _get(obj, "listen_port")
    )


def _vpn_allowed_subnets(obj: Any) -> list[str] | None:
    # Wireguard server uses ``wireguard_server_subnet``; openvpn uses
    # ``openvpn_server_subnet`` or ``ip_subnet``.
    val = (
        _get(obj, "wireguard_server_subnet")
        or _get(obj, "openvpn_server_subnet")
        or _get(obj, "ip_subnet")
        or _get(obj, "allowed_subnets")
    )
    if val is None:
        return None
    if isinstance(val, list):
        return list(val)
    return [str(val)]


@register_serializer(
    tools={
        "unifi_list_vpn_clients": {"kind": RenderKind.LIST},
        "unifi_get_vpn_client_details": {"kind": RenderKind.DETAIL},
    },
)
class VpnClientSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "type", "enabled", "server_address"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "type": _get(obj, "vpn_type") or _get(obj, "purpose"),
            "enabled": bool(_get(obj, "enabled", False)),
            "server_address": _vpn_server_address(obj),
            "last_handshake": _get(obj, "wireguard_client_last_handshake")
            or _get(obj, "last_handshake"),
        }


@register_serializer(
    tools={
        "unifi_list_vpn_servers": {"kind": RenderKind.LIST},
        "unifi_get_vpn_server_details": {"kind": RenderKind.DETAIL},
    },
)
class VpnServerSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "type", "enabled", "listen_port"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "type": _get(obj, "vpn_type") or _get(obj, "purpose"),
            "enabled": bool(_get(obj, "enabled", False)),
            "listen_port": _vpn_listen_port(obj),
            "allowed_subnets": _vpn_allowed_subnets(obj),
        }


@register_serializer(
    tools={
        "unifi_update_vpn_client_state": {"kind": RenderKind.DETAIL},
        "unifi_update_vpn_server_state": {"kind": RenderKind.DETAIL},
    },
)
class VpnMutationAckSerializer(Serializer):
    """DETAIL ack for VPN state-mutation tools.

    Both managers return a bare ``bool`` — coerce to ``{"success": bool}``."""

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
