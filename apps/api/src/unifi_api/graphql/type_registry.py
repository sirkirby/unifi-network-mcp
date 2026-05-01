"""Hybrid projection registry for Phase 6 migration.

During the Phase 6 PR sequence, network/protect/access products migrate
from dict-based serializers to Strawberry types one product at a time.
This registry knows about both kinds and exposes a uniform `lookup()` API
so resolvers + REST routes don't care which kind they're consuming.

At the end of PR4, all entries are types; the kind="serializer" branch
becomes dead code and the registry can collapse to types-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal


class UnknownProjection(KeyError):
    """Raised when no projection (type or serializer) is registered for a resource."""


@dataclass(frozen=True)
class ProjectionEntry:
    kind: Literal["type", "serializer"]
    payload: Any  # the type class OR the serializer instance


class TypeRegistry:
    """Per-product, per-resource projection lookup.

    Types take precedence over serializers when both are registered for the
    same (product, resource) — this gives mid-migration PRs a safety net.
    """

    def __init__(self) -> None:
        self._types: dict[tuple[str, str], Any] = {}
        self._serializers: dict[tuple[str, str], Any] = {}
        # Phase 6 PR2 — read MCP tools whose serializer was migrated to a type
        # need a tool-keyed lookup for the /v1/actions/{tool_name} endpoint.
        # Stores (type_class, kind) where kind is "list" or "detail".
        self._tool_types: dict[str, tuple[Any, str]] = {}

    def register_type(self, product: str, resource: str, type_class: Any) -> None:
        self._types[(product, resource)] = type_class

    def register_tool_type(self, tool_name: str, type_class: Any, kind: str) -> None:
        """Register a Strawberry type as the projection for an MCP tool.

        ``kind`` is the RenderKind value ("list" or "detail") — drives how the
        action endpoint shapes the manager output (list vs single dict).
        """
        self._tool_types[tool_name] = (type_class, kind)

    def lookup_tool(self, tool_name: str) -> tuple[Any, str] | None:
        return self._tool_types.get(tool_name)

    def register_serializer(self, product: str, resource: str, serializer: Any) -> None:
        self._serializers[(product, resource)] = serializer

    def lookup(self, product: str, resource: str) -> ProjectionEntry:
        key = (product, resource)
        if key in self._types:
            return ProjectionEntry(kind="type", payload=self._types[key])
        if key in self._serializers:
            return ProjectionEntry(kind="serializer", payload=self._serializers[key])
        raise UnknownProjection(f"no projection registered for {product}/{resource}")

    def all_resources(self) -> Iterable[tuple[str, str]]:
        return set(self._types.keys()) | set(self._serializers.keys())
