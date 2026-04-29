"""CI gate: every manifest tool must have a registered serializer.

This test is the contributor lint rule for Phase 4A onwards. Adding a new
MCP tool without registering a serializer in apps/api/src/unifi_api/serializers/
will fail this test — the SerializerRegistryError lists the missing tool names
in its message, so the fix is to add the appropriate serializer.

The same invariant is enforced at lifespan startup in server.py
(`discover_serializers(set(manifest.all_tools()))`); this test catches the
regression in CI before the app fails to start.
"""

from unifi_api.serializers._registry import (
    _reset_registry_for_tests,
    discover_serializers,
)
from unifi_api.services.manifest import ManifestRegistry


def test_every_tool_has_a_serializer() -> None:
    _reset_registry_for_tests()
    manifest = ManifestRegistry.load_from_apps()
    # Will raise SerializerRegistryError if any tool lacks a serializer.
    discover_serializers(set(manifest.all_tools()))
