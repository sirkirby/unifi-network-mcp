"""TypeRegistry — Phase 6 hybrid registry that exposes either Strawberry
types (post-migration) OR dict-serializers (still-migrating products).
"""

import pytest

from unifi_api.graphql.type_registry import (
    ProjectionEntry,
    TypeRegistry,
    UnknownProjection,
)


def test_registry_returns_serializer_entry_when_only_serializer_registered() -> None:
    reg = TypeRegistry()
    reg.register_serializer("network", "clients", "fake-serializer-instance")
    entry = reg.lookup("network", "clients")
    assert isinstance(entry, ProjectionEntry)
    assert entry.kind == "serializer"
    assert entry.payload == "fake-serializer-instance"


def test_registry_returns_type_entry_when_type_registered() -> None:
    reg = TypeRegistry()
    reg.register_type("network", "clients", str)  # pretend `str` is a type class
    entry = reg.lookup("network", "clients")
    assert entry.kind == "type"
    assert entry.payload is str


def test_registry_type_overrides_serializer_when_both_registered() -> None:
    """If the same resource has both a type and a serializer registered, the type wins."""
    reg = TypeRegistry()
    reg.register_serializer("network", "clients", "fake")
    reg.register_type("network", "clients", str)
    assert reg.lookup("network", "clients").kind == "type"


def test_registry_raises_unknown_for_missing_resource() -> None:
    reg = TypeRegistry()
    with pytest.raises(UnknownProjection):
        reg.lookup("network", "ghosts")


def test_registry_enumerates_all_resources_as_union() -> None:
    reg = TypeRegistry()
    reg.register_serializer("network", "clients", "s1")
    reg.register_type("protect", "cameras", str)
    items = sorted(reg.all_resources())
    assert items == [("network", "clients"), ("protect", "cameras")]
