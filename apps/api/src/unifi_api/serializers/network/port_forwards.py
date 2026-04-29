"""Port forward serializers (Phase 4A PR1 Cluster 5).

* ``PortForwardSerializer`` — V1 ``/rest/portforward``. The manager
  returns ``PortForward`` aiounifi models on read paths; the underlying
  payload is exposed via ``raw``. ``fwd_protocol`` may also surface as
  ``protocol`` on certain firmware versions, but the manager normalizes
  to ``fwd_protocol``.
* ``PortForwardMutationAckSerializer`` — DETAIL ack for create/update/
  toggle. ``create_*`` returns a dict; ``update_*`` / ``toggle_*`` return
  ``bool``.
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
        "unifi_list_port_forwards": {"kind": RenderKind.LIST},
        "unifi_get_port_forward": {"kind": RenderKind.DETAIL},
    },
)
class PortForwardSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "enabled", "fwd_protocol", "dst_port", "fwd_port"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "enabled": bool(_get(obj, "enabled", False)),
            "fwd_protocol": _get(obj, "fwd_protocol") or _get(obj, "protocol"),
            "dst_port": _get(obj, "dst_port"),
            "fwd_port": _get(obj, "fwd_port"),
            "src": _get(obj, "src"),
            "log": bool(_get(obj, "log", False)),
        }


@register_serializer(
    tools={
        "unifi_create_port_forward": {"kind": RenderKind.DETAIL},
        "unifi_create_simple_port_forward": {"kind": RenderKind.DETAIL},
        "unifi_update_port_forward": {"kind": RenderKind.DETAIL},
        "unifi_toggle_port_forward": {"kind": RenderKind.DETAIL},
    },
)
class PortForwardMutationAckSerializer(Serializer):
    """DETAIL ack for port forward mutations.

    ``create_*`` returns a dict (or None); ``update_*`` / ``toggle_*``
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
        if obj is None:
            return {"success": False}
        return {"result": str(obj)}
