"""Client group + usergroup serializers (Phase 4A PR1 Cluster 2).

UniFi exposes two parallel "group" entities under different APIs:

* ``ClientGroupManager`` — V2 ``/network-members-group`` endpoint, used for
  OON/firewall membership grouping. Manager returns ``List[Dict]`` (list),
  ``Optional[Dict]`` (create/get-by-id), and ``bool`` (update/delete).
* ``UsergroupManager`` — V1 ``/rest/usergroup`` endpoint, used for QoS
  bandwidth limits. Manager returns ``List[Dict]`` (list / details), an
  ``Optional[Dict]`` (create), and ``bool`` (update).

Both expose the same useful list/detail fields (``_id``, ``name``,
``qos_rate_max_down``, ``qos_rate_max_up``) so we render them with the same
shape. Mutations across both managers normalise to ``{"success": bool}``
when the manager returns a bare ``bool`` to satisfy the DETAIL contract
(spec section 5 EMPTY discipline).
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
        "unifi_list_client_groups": {"kind": RenderKind.LIST},
        "unifi_get_client_group_details": {"kind": RenderKind.DETAIL},
    },
)
class ClientGroupSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "qos_rate_max_down", "qos_rate_max_up"]

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "qos_rate_max_down": _get(obj, "qos_rate_max_down"),
            "qos_rate_max_up": _get(obj, "qos_rate_max_up"),
        }


@register_serializer(
    tools={
        "unifi_list_usergroups": {"kind": RenderKind.LIST},
        "unifi_get_usergroup_details": {"kind": RenderKind.DETAIL},
    },
)
class UserGroupSerializer(Serializer):
    primary_key = "id"
    display_columns = ["name", "qos_rate_max_down", "qos_rate_max_up"]

    @staticmethod
    def serialize(obj) -> dict:
        return {
            "id": _get(obj, "_id") or _get(obj, "id"),
            "name": _get(obj, "name"),
            "qos_rate_max_down": _get(obj, "qos_rate_max_down"),
            "qos_rate_max_up": _get(obj, "qos_rate_max_up"),
        }


@register_serializer(
    tools={
        "unifi_create_client_group": {"kind": RenderKind.DETAIL},
        "unifi_update_client_group": {"kind": RenderKind.DETAIL},
        "unifi_delete_client_group": {"kind": RenderKind.DETAIL},
        "unifi_create_usergroup": {"kind": RenderKind.DETAIL},
        "unifi_update_usergroup": {"kind": RenderKind.DETAIL},
    },
)
class ClientGroupMutationAckSerializer(Serializer):
    """Generic ack for client_group / usergroup mutations.

    Manager returns vary: ``update_*``/``delete_*`` return ``bool``, while
    ``create_*`` returns the created dict. Coerce both to a DETAIL-shaped
    payload."""

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
