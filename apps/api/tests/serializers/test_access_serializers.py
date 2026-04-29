"""Access serializer unit tests — one fixture per resource.

Access managers in unifi-core return plain dicts (proxy path returns the
raw location/user/credential dicts; API-client path returns flattened dicts).
Each fixture below mirrors the proxy-path shape, since that's the richer one
the catalog will most often see.
"""

from unifi_api.serializers._registry import (
    discover_serializers,
    serializer_registry_singleton,
)


def _registry():
    """Trigger discovery once for the test module."""
    discover_serializers(manifest_tool_names=set())
    return serializer_registry_singleton()


def test_door_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_resource("access", "doors")
    sample = {
        "id": "door1",
        "name": "Front Door",
        "location_type": "door",
        "is_online": True,
        "door_position_status": "close",
        "lock_relay_status": "lock",
        "devices": [{"id": "dev1", "name": "G2 Reader", "online": True}],
        "last_event": {
            "name": "Access Granted",
            "timestamp": "2026-04-29T10:00:00+00:00",
        },
    }
    out = s.serialize(sample)
    assert out["id"] == "door1"
    assert out["name"] == "Front Door"
    assert "location" in out
    assert "is_online" in out
    assert "is_locked" in out
    assert "lock_state" in out
    assert "last_event" in out


def test_user_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_resource("access", "users")
    sample = {
        "id": "user1",
        "first_name": "Ada",
        "last_name": "Lovelace",
        "name": "Ada Lovelace",
        "employee_id": "E-1815",
        "status": "active",
        "role": "admin",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    out = s.serialize(sample)
    assert out["id"] == "user1"
    assert out["name"] == "Ada Lovelace"
    assert out["employee_id"] == "E-1815"
    assert out["status"] == "active"
    assert out["role"] == "admin"
    assert out["created_at"] == "2026-01-01T00:00:00+00:00"


def test_credential_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_resource("access", "credentials")
    sample = {
        "id": "cred1",
        "user_id": "user1",
        "type": "nfc_card",
        "status": "active",
        "expiry": "2027-01-01T00:00:00+00:00",
        "last_used": "2026-04-28T18:30:00+00:00",
    }
    out = s.serialize(sample)
    assert out["id"] == "cred1"
    assert out["user_id"] == "user1"
    assert out["type"] == "nfc_card"
    assert out["status"] == "active"
    assert out["expiry"] == "2027-01-01T00:00:00+00:00"
    assert out["last_used"] == "2026-04-28T18:30:00+00:00"
