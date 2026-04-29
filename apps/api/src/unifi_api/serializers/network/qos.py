"""QoS rule serializers (Phase 4A PR1 Cluster 4).

``QosManager`` exposes:

* ``get_qos_rules()`` → ``List[Dict]`` (V2 ``/qos-rules``; controller wraps
  in ``{"data": [...]}`` which the manager unwraps)
* ``get_qos_rule_details(rule_id)`` → ``Optional[Dict]``
* ``create_qos_rule(rule_data)`` → ``Optional[Dict]``
* ``update_qos_rule(rule_id, data)`` → ``bool``
* ``delete_qos_rule(rule_id)`` → ``bool``

The toggle / simple-create helpers live on the QoS *tool* layer and end
up calling ``update_qos_rule`` / ``create_qos_rule``; both still resolve
to ``bool`` / ``dict`` results.

Surface fields ``rate_max_down`` / ``rate_max_up`` and ``priority`` so the
LIST render can show the numbers a human cares about; everything else is
preserved on the wrapped object via the registry's normal serialize flow.
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
        "unifi_list_qos_rules": {"kind": RenderKind.LIST},
        "unifi_get_qos_rule_details": {"kind": RenderKind.DETAIL},
    },
)
class QosRuleSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "enabled", "priority", "rate_max_down", "rate_max_up"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "enabled": bool(_get(obj, "enabled", False)),
            "rate_max_down": _get(obj, "rate_max_down"),
            "rate_max_up": _get(obj, "rate_max_up"),
            "priority": _get(obj, "priority"),
        }


@register_serializer(
    tools={
        "unifi_create_qos_rule": {"kind": RenderKind.DETAIL},
        "unifi_create_simple_qos_rule": {"kind": RenderKind.DETAIL},
        "unifi_update_qos_rule": {"kind": RenderKind.DETAIL},
        "unifi_toggle_qos_rule_enabled": {"kind": RenderKind.DETAIL},
    },
)
class QosMutationAckSerializer(Serializer):
    """DETAIL ack for QoS rule mutations.

    ``create_*`` returns the created dict; ``update_*`` and toggle
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
