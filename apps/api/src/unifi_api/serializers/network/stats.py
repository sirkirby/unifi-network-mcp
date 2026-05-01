"""Stats — Phase 6 PR2 Task 23 migrated.

The TIMESERIES + DETAIL projections moved to Strawberry types at
``unifi_api.graphql.types.network.stat``:

- TIMESERIES (``StatPoint``):
    * ``unifi_get_dashboard``
    * ``unifi_get_network_stats``
    * ``unifi_get_gateway_stats``
    * ``unifi_get_client_dpi_traffic``
    * ``unifi_get_site_dpi_traffic``
    * ``unifi_get_device_stats``
    * ``unifi_get_client_stats``

- DETAIL (``DpiStats``):
    * ``unifi_get_dpi_stats``

This module is intentionally empty — the type_registry handles every stats
tool. The ``PHASE6_TYPE_MIGRATED_TOOLS`` allowlist exempts them from the
strict serializer coverage gate.
"""
