"""Serializer registry: lookup helpers + auto-discovery + manifest validation."""

from __future__ import annotations

import importlib
import pkgutil
import sys
from typing import Iterable

from unifi_api.serializers import _base
from unifi_api.serializers._base import (
    RenderKind, Serializer,
    _TOOL_REGISTRY, _RESOURCE_REGISTRY,
    _TOOL_KIND_OVERRIDES, _RESOURCE_KIND_OVERRIDES,
    _reset_registries_for_tests,
)


class SerializerRegistryError(Exception):
    """Raised when the registry is in an invalid state (e.g., missing serializer)."""


# Phase 6 PR2 migration: read tools whose dict-shaping logic moved from
# serializers to Strawberry types in unifi_api.graphql.types.<product>.<resource>.
# These tools are covered by the type_registry instead of the serializer
# registry. Task 27 will repoint the coverage gate to type_registry directly
# and this constant will be removed.
PHASE6_TYPE_MIGRATED_TOOLS: frozenset[str] = frozenset({
    # Task 19 — network/clients
    "unifi_list_clients",
    "unifi_get_client_details",
    "unifi_list_blocked_clients",
    "unifi_lookup_by_ip",
    # Task 20 — network/devices
    "unifi_list_devices",
    "unifi_get_device_details",
    "unifi_get_device_radio",
    "unifi_get_lldp_neighbors",
    "unifi_list_rogue_aps",
    "unifi_list_known_rogue_aps",
    "unifi_get_rf_scan_results",
    "unifi_list_available_channels",
    "unifi_get_speedtest_status",
    # Task 21 — network/networks
    "unifi_list_networks",
    "unifi_get_network_details",
    # Task 21 — network/wlans
    "unifi_list_wlans",
    "unifi_get_wlan_details",
    # Task 21 — network/vpn
    "unifi_list_vpn_clients",
    "unifi_get_vpn_client_details",
    "unifi_list_vpn_servers",
    "unifi_get_vpn_server_details",
    # Task 21 — network/dns
    "unifi_list_dns_records",
    "unifi_get_dns_record_details",
    # Task 21 — network/routes
    "unifi_list_routes",
    "unifi_get_route_details",
    "unifi_list_active_routes",
    "unifi_list_traffic_routes",
    "unifi_get_traffic_route_details",
})


class SerializerRegistry:
    def serializer_for_tool(self, tool_name: str) -> Serializer:
        s = _TOOL_REGISTRY.get(tool_name)
        if s is None:
            raise SerializerRegistryError(f"no serializer registered for tool '{tool_name}'")
        return s

    def serializer_for_resource(self, product: str, resource: str) -> Serializer:
        s = _RESOURCE_REGISTRY.get((product, resource))
        if s is None:
            raise SerializerRegistryError(
                f"no serializer registered for resource ({product}, {resource})"
            )
        return s

    def kind_for_tool(self, tool_name: str) -> RenderKind:
        if tool_name in _TOOL_KIND_OVERRIDES:
            return _TOOL_KIND_OVERRIDES[tool_name]
        return self.serializer_for_tool(tool_name).kind

    def kind_for_resource(self, product: str, resource: str) -> RenderKind:
        key = (product, resource)
        if key in _RESOURCE_KIND_OVERRIDES:
            return _RESOURCE_KIND_OVERRIDES[key]
        return self.serializer_for_resource(product, resource).kind

    def all_tools(self) -> Iterable[str]:
        return list(_TOOL_REGISTRY.keys())

    def all_resources(self) -> Iterable[tuple[str, str]]:
        return list(_RESOURCE_REGISTRY.keys())

    def render_hint_for_tool(self, tool_name: str) -> dict:
        s = self.serializer_for_tool(tool_name)
        kind = self.kind_for_tool(tool_name)
        return s._render_hint(kind)

    def render_hint_for_resource(self, product: str, resource: str) -> dict:
        s = self.serializer_for_resource(product, resource)
        kind = self.kind_for_resource(product, resource)
        return s._render_hint(kind)

    def validate_manifest(self, manifest_tool_names: set[str]) -> None:
        """Every tool in the manifest must have a serializer registered, except
        Phase 6-migrated read tools whose projections live in the type_registry."""
        missing = (
            manifest_tool_names
            - set(_TOOL_REGISTRY.keys())
            - PHASE6_TYPE_MIGRATED_TOOLS
        )
        if missing:
            raise SerializerRegistryError(
                f"missing serializer for {len(missing)} tools: {sorted(missing)[:5]}..."
            )


_singleton: SerializerRegistry | None = None


def serializer_registry_singleton() -> SerializerRegistry:
    global _singleton
    if _singleton is None:
        _singleton = SerializerRegistry()
    return _singleton


def discover_serializers(manifest_tool_names: set[str]) -> SerializerRegistry:
    """Walk the serializers package, import every submodule (decorators self-register),
    then validate against the manifest. Called once during lifespan startup."""
    pkg = importlib.import_module("unifi_api.serializers")
    for product in ("network", "protect", "access"):
        try:
            product_pkg = importlib.import_module(f"unifi_api.serializers.{product}")
        except ModuleNotFoundError:
            continue
        for _, modname, ispkg in pkgutil.iter_modules(product_pkg.__path__):
            if ispkg or modname.startswith("_"):
                continue
            importlib.import_module(f"unifi_api.serializers.{product}.{modname}")
    reg = serializer_registry_singleton()
    reg.validate_manifest(manifest_tool_names)
    return reg


def _reset_registry_for_tests() -> None:
    """For test isolation — drops module-level registries AND evicts serializer
    submodules from sys.modules so the next discover_serializers re-imports
    them and re-runs the @register_serializer decorators. Without the eviction,
    importlib.import_module is a no-op for already-loaded modules and the
    registry stays empty after reset."""
    global _singleton
    _reset_registries_for_tests()
    _singleton = None
    for product in ("network", "protect", "access"):
        prefix = f"unifi_api.serializers.{product}"
        for modname in list(sys.modules.keys()):
            if modname == prefix or modname.startswith(prefix + "."):
                sys.modules.pop(modname, None)
