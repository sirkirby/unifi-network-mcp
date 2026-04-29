"""Access system info + health serializers.

``SystemManager.get_system_info`` returns either a connectivity probe
dict (api_client path: ``source``, ``host``, ``api_port``, ``connected``,
``door_count``) or the raw ``access/info`` proxy payload (which carries
``name``, ``version``, ``hostname``, ``uptime``, etc.). We normalize to
the catalog spec fields, falling back to whatever the probe path
exposes.

``SystemManager.get_health`` returns a per-probe status dict
(``api_client_healthy``, ``proxy_healthy``, etc.). We derive a single
``status`` field plus optional door/device counts when the caller
supplies them via ``num_*`` keys.
"""

from typing import Any

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _derive_health_status(obj: Any) -> str:
    explicit = _get(obj, "status")
    if isinstance(explicit, str):
        return explicit
    api_h = _get(obj, "api_client_healthy")
    proxy_h = _get(obj, "proxy_healthy")
    flags = [v for v in (api_h, proxy_h) if v is not None]
    if not flags:
        is_connected = _get(obj, "is_connected")
        return "healthy" if is_connected else "unknown"
    if all(flags):
        return "healthy"
    if any(flags):
        return "degraded"
    return "unhealthy"


@register_serializer(
    tools={
        "access_get_system_info": {"kind": RenderKind.DETAIL},
    },
)
class AccessSystemInfoSerializer(Serializer):
    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "name": _get(obj, "name") or _get(obj, "source"),
            "version": _get(obj, "version"),
            "hostname": _get(obj, "hostname") or _get(obj, "host"),
            "uptime": _get(obj, "uptime"),
        }


@register_serializer(
    tools={
        "access_get_health": {"kind": RenderKind.DETAIL},
    },
)
class AccessHealthSerializer(Serializer):
    kind = RenderKind.DETAIL

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "status": _derive_health_status(obj),
            "num_doors": _get(obj, "num_doors"),
            "num_devices": _get(obj, "num_devices"),
            "num_offline_devices": _get(obj, "num_offline_devices"),
        }
