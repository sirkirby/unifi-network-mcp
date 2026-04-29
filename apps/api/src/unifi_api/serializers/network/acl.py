"""ACL rule serializers (Phase 4A PR1 Cluster 4).

``AclManager`` exposes ``get_acl_rules()`` / ``get_acl_rule_by_id()`` /
``create_acl_rule()`` / ``update_acl_rule()`` / ``delete_acl_rule()`` on
V2 ``/acl-rules``. ``GET /acl-rules/{id}`` returns 405, so detail lookups
are served by list-then-filter inside the manager — both LIST and DETAIL
receive the same dict shape here.

The API stores source/destination match config under ``traffic_source`` /
``traffic_destination``; we surface them as ``source`` / ``destination``
to match the firewall-rule serializer's vocabulary.
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
        "unifi_list_acl_rules": {"kind": RenderKind.LIST},
        "unifi_get_acl_rule_details": {"kind": RenderKind.DETAIL},
    },
)
class AclRuleSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "enabled", "action"]
    sort_default = "name:asc"

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "enabled": bool(_get(obj, "enabled", False)),
            "action": _get(obj, "action"),
            "source": _get(obj, "traffic_source") or _get(obj, "source"),
            "destination": _get(obj, "traffic_destination")
            or _get(obj, "destination"),
        }


@register_serializer(
    tools={
        "unifi_create_acl_rule": {"kind": RenderKind.DETAIL},
        "unifi_update_acl_rule": {"kind": RenderKind.DETAIL},
        "unifi_delete_acl_rule": {"kind": RenderKind.DETAIL},
    },
)
class AclMutationAckSerializer(Serializer):
    """DETAIL ack for ACL rule mutations.

    ``create_acl_rule`` returns the created dict; update + delete return
    ``bool``."""

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
