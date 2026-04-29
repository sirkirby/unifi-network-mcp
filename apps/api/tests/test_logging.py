"""Structured logging tests."""

import json

from unifi_api.logging import configure_logging, get_logger


def test_emits_json_with_required_fields(capsys) -> None:
    configure_logging(level="INFO")
    log = get_logger("test")
    log.info("event_happened", extra={"request_id": "req-123", "controller": "default"})
    captured = capsys.readouterr().err.strip().splitlines()
    assert captured, "expected one JSON log line on stderr"
    payload = json.loads(captured[-1])
    assert payload["level"] == "INFO"
    assert payload["event"] == "event_happened"
    assert payload["request_id"] == "req-123"
    assert payload["controller"] == "default"
    assert "ts" in payload


def test_respects_level(capsys) -> None:
    configure_logging(level="WARNING")
    log = get_logger("test")
    log.info("hidden")
    log.warning("shown")
    captured = capsys.readouterr().err.strip().splitlines()
    assert len(captured) == 1
    assert json.loads(captured[0])["event"] == "shown"
