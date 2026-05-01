"""Client sessions and wifi-details — Phase 6 PR2 Task 23 migrated.

Both read shapes (LIST + DETAIL) moved to Strawberry types at
``unifi_api.graphql.types.network.session``:

- ``unifi_get_client_sessions`` (LIST) → ``ClientSession``
- ``unifi_get_client_wifi_details`` (DETAIL) → ``ClientWifiDetails``

This module is intentionally empty — the type_registry handles both tools.
The ``PHASE6_TYPE_MIGRATED_TOOLS`` allowlist in
``unifi_api.serializers._registry`` exempts them from the strict serializer
coverage gate.
"""
