"""Client group + usergroup mutation ack serializer (Phase 4A PR1 Cluster 2).

Phase 6 PR2 Task 24 — read shapes (ClientGroupSerializer, UserGroupSerializer)
migrated to Strawberry types in
``unifi_api.graphql.types.network.client_group``. Only the mutation ack
remains here so create/update/delete continue to dispatch through the
serializer registry across both manager kinds.

UniFi exposes two parallel "group" entities under different APIs:

* ``ClientGroupManager`` — V2 ``/network-members-group`` endpoint, used for
  OON/firewall membership grouping. Returns ``Optional[Dict]`` (create) or
  ``bool`` (update/delete).
* ``UsergroupManager`` — V1 ``/rest/usergroup`` endpoint, used for QoS
  bandwidth limits. Returns ``Optional[Dict]`` (create) or ``bool``
  (update).

Mutations across both managers normalise to ``{"success": bool}`` when the
manager returns a bare ``bool`` to satisfy the DETAIL contract (spec
section 5 EMPTY discipline).
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


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
