"""Hotspot voucher mutation ack serializer.

Phase 6 PR2 Task 23 migrated the read shape (Voucher LIST + DETAIL) to a
Strawberry type at ``unifi_api.graphql.types.network.voucher``. Only the
mutation ack remains here — it covers create + revoke for hotspot vouchers.

* ``create_voucher`` returns a list of new voucher dicts (or ``None``).
* ``revoke_voucher`` returns ``bool``.
"""

from unifi_api.serializers._base import RenderKind, Serializer, register_serializer


@register_serializer(
    tools={
        "unifi_create_voucher": {"kind": RenderKind.DETAIL},
        "unifi_revoke_voucher": {"kind": RenderKind.DETAIL},
    },
)
class VoucherMutationAckSerializer(Serializer):
    """DETAIL ack for voucher create + revoke.

    ``create_voucher`` returns a list of new voucher dicts (or ``None``);
    ``revoke_voucher`` returns ``bool``."""

    @staticmethod
    def serialize(obj) -> dict:
        if isinstance(obj, bool):
            return {"success": obj}
        if isinstance(obj, list):
            return {"success": True, "vouchers": obj}
        if isinstance(obj, dict):
            return obj
        if obj is None:
            return {"success": False}
        return {"result": str(obj)}
