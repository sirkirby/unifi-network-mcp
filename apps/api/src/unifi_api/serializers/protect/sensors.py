"""Protect sensor serializers — fully migrated to Strawberry types.

Phase 6 PR3 Task C — the single read serializer (``SensorSerializer``)
moved to a Strawberry type in
``unifi_api.graphql.types.protect.sensors``. The
``protect_list_sensors`` tool is listed in
``PHASE6_TYPE_MIGRATED_TOOLS`` and dispatched via the type_registry by
both the REST route and the action endpoint.

There are no mutation serializers in this module — ``SensorManager``
exposes no preview-and-confirm flows today.
"""
