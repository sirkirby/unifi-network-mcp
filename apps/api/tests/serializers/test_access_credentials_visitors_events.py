"""Access credentials + visitors + events serializer tests
(Phase 4A PR3 Cluster 2).

Manager methods covered:
  - ``CredentialManager.create_credential`` / ``revoke_credential`` -> preview dicts
  - ``VisitorManager.list_visitors`` -> list[dict]
  - ``VisitorManager.get_visitor`` -> dict
  - ``VisitorManager.create_visitor`` / ``delete_visitor`` -> preview dicts
  - ``EventManager.list_events`` -> list[dict]  (event log)
  - ``EventManager.get_event`` -> dict (event detail)
  - ``EventManager.get_recent_from_buffer`` -> list[dict]  (event log)
  - ``EventManager.get_activity_summary`` -> dict (histogram payload)

The ``access_subscribe_events`` tool has no AST-discoverable manager call
(it composes a dict from ``event_manager.buffer_size``); the serializer
still needs to be registered for coverage. Phase 4B PR3 Task 14 migrates
this to ``AccessStreamSubscriptionSerializer`` (STREAM kind) returning
``{stream_url, transport: "sse", buffer_size, instructions}``.
"""

from unifi_api.serializers._registry import (
    discover_serializers,
    serializer_registry_singleton,
)


def _registry():
    discover_serializers(manifest_tool_names=set())
    return serializer_registry_singleton()


# ---- credentials (mutation acks) ----


def test_credential_mutation_ack_create() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("access_create_credential")
    sample = {
        "credential_type": "nfc",
        "credential_data": {"user_id": "user-1", "token": "abc123"},
        "proposed_changes": {"action": "create", "type": "nfc", "user_id": "user-1"},
    }
    out = s.serialize_action(sample, tool_name="access_create_credential")
    assert out["success"] is True
    assert out["data"]["credential_type"] == "nfc"
    assert out["data"]["proposed_changes"]["action"] == "create"
    assert out["render_hint"]["kind"] == "detail"


def test_credential_mutation_ack_revoke() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("access_revoke_credential")
    sample = {
        "credential_id": "cred-001",
        "current_state": {"id": "cred-001", "user_id": "user-1", "type": "nfc"},
        "proposed_changes": {"action": "revoke"},
    }
    out = s.serialize_action(sample, tool_name="access_revoke_credential")
    assert out["success"] is True
    assert out["data"]["credential_id"] == "cred-001"
    assert out["render_hint"]["kind"] == "detail"


# ---- visitors ----


def test_visitor_list_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("access_list_visitors")
    sample = [
        {
            "id": "vis-001",
            "name": "Jane Doe",
            "host_user_id": "user-1",
            "valid_from": "2026-04-29T08:00:00Z",
            "valid_until": "2026-04-29T18:00:00Z",
            "status": "active",
            "credential_count": 1,
        }
    ]
    out = s.serialize_action(sample, tool_name="access_list_visitors")
    assert out["success"] is True
    assert out["data"][0]["id"] == "vis-001"
    assert out["data"][0]["name"] == "Jane Doe"
    assert out["data"][0]["status"] == "active"
    assert out["render_hint"]["kind"] == "list"


def test_visitor_detail_serializer_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("access_get_visitor")
    sample = {
        "id": "vis-002",
        "name": "John Roe",
        "host_user_id": "user-2",
        "valid_from": "2026-04-29T09:00:00Z",
        "valid_until": "2026-04-29T17:00:00Z",
        "status": "scheduled",
        "credential_count": 0,
    }
    out = s.serialize_action(sample, tool_name="access_get_visitor")
    assert out["success"] is True
    assert out["data"]["id"] == "vis-002"
    assert out["data"]["host_user_id"] == "user-2"
    assert out["render_hint"]["kind"] == "detail"


def test_visitor_mutation_ack_create() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("access_create_visitor")
    sample = {
        "visitor_data": {
            "name": "Alice",
            "access_start": "2026-04-29T08:00:00Z",
            "access_end": "2026-04-29T18:00:00Z",
        },
        "proposed_changes": {"action": "create", "name": "Alice"},
    }
    out = s.serialize_action(sample, tool_name="access_create_visitor")
    assert out["success"] is True
    assert out["data"]["visitor_data"]["name"] == "Alice"
    assert out["data"]["proposed_changes"]["action"] == "create"
    assert out["render_hint"]["kind"] == "detail"


def test_visitor_mutation_ack_delete() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("access_delete_visitor")
    sample = {
        "visitor_id": "vis-001",
        "visitor_name": "Jane Doe",
        "current_state": {"id": "vis-001", "name": "Jane Doe"},
        "proposed_changes": {"action": "delete"},
    }
    out = s.serialize_action(sample, tool_name="access_delete_visitor")
    assert out["success"] is True
    assert out["data"]["visitor_id"] == "vis-001"
    assert out["render_hint"]["kind"] == "detail"


# ---- events ----


def test_access_event_log_list_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("access_list_events")
    sample = [
        {
            "id": "evt-1",
            "type": "access_granted",
            "timestamp": "2026-04-29T08:00:00Z",
            "door_id": "door-1",
            "user_id": "user-1",
            "credential_id": "cred-001",
            "result": "granted",
        }
    ]
    out = s.serialize_action(sample, tool_name="access_list_events")
    assert out["success"] is True
    assert out["data"][0]["id"] == "evt-1"
    assert out["data"][0]["result"] == "granted"
    assert out["render_hint"]["kind"] == "event_log"


def test_access_recent_events_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("access_recent_events")
    sample = [
        {
            "id": "evt-2",
            "type": "access_denied",
            "timestamp": "2026-04-29T08:01:00Z",
            "door_id": "door-1",
            "user_id": "user-2",
            "credential_id": None,
            "result": "denied",
        }
    ]
    out = s.serialize_action(sample, tool_name="access_recent_events")
    assert out["success"] is True
    assert out["data"][0]["id"] == "evt-2"
    assert out["data"][0]["result"] == "denied"
    assert out["render_hint"]["kind"] == "event_log"


def test_access_event_detail_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("access_get_event")
    sample = {
        "id": "evt-3",
        "type": "door_open",
        "timestamp": "2026-04-29T08:02:00Z",
        "door_id": "door-2",
        "user_id": "user-3",
        "credential_id": "cred-002",
        "result": "granted",
    }
    out = s.serialize_action(sample, tool_name="access_get_event")
    assert out["success"] is True
    assert out["data"]["id"] == "evt-3"
    assert out["data"]["door_id"] == "door-2"
    assert out["render_hint"]["kind"] == "detail"


def test_activity_summary_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("access_get_activity_summary")
    sample = {
        "period_start": "2026-04-22T00:00:00Z",
        "period_end": "2026-04-29T00:00:00Z",
        "total_events": 142,
        "granted_count": 130,
        "denied_count": 12,
        "top_users": [{"user_id": "user-1", "count": 47}],
    }
    out = s.serialize_action(sample, tool_name="access_get_activity_summary")
    assert out["success"] is True
    assert out["data"]["total_events"] == 142
    assert out["data"]["granted_count"] == 130
    assert out["data"]["top_users"][0]["user_id"] == "user-1"
    assert out["render_hint"]["kind"] == "detail"


def test_subscribe_events_shape() -> None:
    reg = _registry()
    s = reg.serializer_for_tool("access_subscribe_events")
    sample = {
        "resource_uri": "access://events/stream",
        "summary_uri": "access://events/stream/summary",
        "instructions": "Read the resource at ...",
        "buffer_size": 100,
    }
    out = s.serialize_action(sample, tool_name="access_subscribe_events")
    assert out["success"] is True
    assert out["data"]["stream_url"] == "/v1/streams/access/events"
    assert out["data"]["transport"] == "sse"
    assert out["data"]["buffer_size"] == 100
    assert out["data"]["instructions"] == "Read the resource at ..."
    assert out["render_hint"]["kind"] == "stream"


def test_subscribe_events_non_dict_input() -> None:
    """Non-dict inputs still surface the stream metadata."""
    reg = _registry()
    s = reg.serializer_for_tool("access_subscribe_events")
    out = s.serialize_action("sub-xyz-789", tool_name="access_subscribe_events")
    assert out["success"] is True
    assert out["data"]["stream_url"] == "/v1/streams/access/events"
    assert out["data"]["transport"] == "sse"
    assert out["render_hint"]["kind"] == "stream"
