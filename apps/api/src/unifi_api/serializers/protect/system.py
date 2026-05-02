"""Protect system serializers — fully migrated to Strawberry types.

Phase 6 PR3 Task C — all four read serializers
(``ProtectSystemInfoSerializer``, ``ProtectHealthSerializer``,
``FirmwareStatusSerializer``, ``ViewerSerializer``) moved to Strawberry
types in ``unifi_api.graphql.types.protect.system``. Their tools
(``protect_get_system_info``, ``protect_get_health``,
``protect_get_firmware_status``, ``protect_list_viewers``) are listed
in ``PHASE6_TYPE_MIGRATED_TOOLS`` and dispatched via the type_registry
by both REST routes and the action endpoint.

There are no mutation serializers in this module — ``SystemManager``
exposes no preview-and-confirm flows today (system reboot lives in a
different module).
"""
