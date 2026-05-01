"""Switch + port-related mutation ack serializer (Phase 4A PR1 Cluster 1).

Phase 6 PR2 Task 24 — read shapes (port_profiles, switch_ports, port_stats,
switch_capabilities) migrated to Strawberry types in
``unifi_api.graphql.types.network.switch``. Only the mutation ack remains
here so ``set_*``, ``configure_*``, ``power_cycle_*``,
``create/update/delete_port_profile``, ``set_jumbo_frames`` and
``update_switch_stp`` continue to dispatch through the serializer registry.

Mutation ack normalisation: managers return ``bool`` (most CUD ops) or a
``dict`` (e.g. ``create_port_profile`` returns the created profile). Both
shapes are coerced to a DETAIL-shaped payload per spec section 5
(EMPTY discipline — prefer DETAIL with a tiny shape).
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


# Mutation acks — DETAIL with tiny shape (spec section 5 EMPTY discipline).
# Manager methods here return bool/dict; we normalise to a small DETAIL payload.
@register_serializer(
    tools={
        "unifi_create_port_profile": {"kind": RenderKind.DETAIL},
        "unifi_update_port_profile": {"kind": RenderKind.DETAIL},
        "unifi_delete_port_profile": {"kind": RenderKind.DETAIL},
        "unifi_set_switch_port_profile": {"kind": RenderKind.DETAIL},
        "unifi_configure_port_aggregation": {"kind": RenderKind.DETAIL},
        "unifi_configure_port_mirror": {"kind": RenderKind.DETAIL},
        "unifi_power_cycle_port": {"kind": RenderKind.DETAIL},
        "unifi_set_jumbo_frames": {"kind": RenderKind.DETAIL},
        "unifi_update_switch_stp": {"kind": RenderKind.DETAIL},
    },
)
class SwitchMutationAckSerializer(Serializer):
    """Generic ack for switch-side mutations. Most managers return ``bool``
    — coerce to ``{"success": bool}``. Dict responses (e.g. ``create_port_profile``
    returns the created profile) pass through with minimal coercion."""

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
