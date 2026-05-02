"""Resource-keyed and tool-keyed projection registry for typed Strawberry classes.

Phase 6 close: all 34 read resources and 122 read tools are projected via
Strawberry types. The Phase 6 migration window's hybrid serializer-fallback
branch is dead code and removed.

Mutation tools (the 115 ones in serializer_registry.all_tools()) continue
to use the legacy serializer_registry's serializer_for_tool() path on the
REST /v1/actions/{tool} endpoint. Those serializers live in serializers/
and are out of scope for type_registry.
"""

from __future__ import annotations

from typing import Any, Iterable


class UnknownProjection(KeyError):
    """Raised when no type is registered for a resource."""


class TypeRegistry:
    """Per-product, per-resource (and per-tool) Strawberry type lookup."""

    def __init__(self) -> None:
        self._types: dict[tuple[str, str], Any] = {}
        # Tool-keyed lookups for the /v1/actions/{tool_name} endpoint and
        # tool-only routes. Stores (type_class, kind) where kind is the
        # RenderKind value ("list" / "detail" / "timeseries" / "event_log").
        self._tool_types: dict[str, tuple[Any, str]] = {}

    def register_type(self, product: str, resource: str, type_class: Any) -> None:
        self._types[(product, resource)] = type_class

    def register_tool_type(self, tool_name: str, type_class: Any, kind: str) -> None:
        """Register a Strawberry type as the projection for a read tool.

        ``kind`` is the RenderKind value ("list" / "detail" / "timeseries" /
        "event_log") — drives how the action endpoint shapes the manager
        output (list vs single dict).
        """
        self._tool_types[tool_name] = (type_class, kind)

    def lookup(self, product: str, resource: str) -> Any:
        """Return the Strawberry type class for a (product, resource) projection."""
        try:
            return self._types[(product, resource)]
        except KeyError:
            raise UnknownProjection(f"no type registered for {product}/{resource}")

    def lookup_tool(self, tool_name: str) -> tuple[Any, str] | None:
        return self._tool_types.get(tool_name)

    def all_resources(self) -> Iterable[tuple[str, str]]:
        return self._types.keys()

    def all_tools(self) -> Iterable[str]:
        return self._tool_types.keys()
