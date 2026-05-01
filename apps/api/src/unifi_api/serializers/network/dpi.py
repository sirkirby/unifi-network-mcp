"""DPI serializers — fully migrated to Strawberry types.

Phase 6 PR2 Task 22 migrated both read shapes (DpiApplication, DpiCategory)
to Strawberry types at ``unifi_api.graphql.types.network.dpi``. DPI is a
read-only resource (no create/update/delete tools), so no mutation ack
serializer is needed. The module is preserved as a stub so the auto-discovery
walker still finds an importable submodule under
``unifi_api.serializers.network``; once the type_registry replaces the
serializer registry entirely, this file can be removed.
"""
