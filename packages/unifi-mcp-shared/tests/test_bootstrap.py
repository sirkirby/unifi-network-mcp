"""Tests for the shared bootstrap module."""

import logging
import os

import pytest

from unifi_mcp_shared.bootstrap import validate_registration_mode


class TestValidateRegistrationMode:
    """Tests for validate_registration_mode."""

    def test_default_is_lazy(self, monkeypatch):
        monkeypatch.delenv("UNIFI_TOOL_REGISTRATION_MODE", raising=False)
        mode = validate_registration_mode(logging.getLogger("test"))
        assert mode == "lazy"

    def test_eager(self, monkeypatch):
        monkeypatch.setenv("UNIFI_TOOL_REGISTRATION_MODE", "eager")
        assert validate_registration_mode(logging.getLogger("test")) == "eager"

    def test_meta_only(self, monkeypatch):
        monkeypatch.setenv("UNIFI_TOOL_REGISTRATION_MODE", "meta_only")
        assert validate_registration_mode(logging.getLogger("test")) == "meta_only"

    def test_invalid_falls_back_to_lazy(self, monkeypatch):
        monkeypatch.setenv("UNIFI_TOOL_REGISTRATION_MODE", "invalid_mode")
        mode = validate_registration_mode(logging.getLogger("test"))
        assert mode == "lazy"

    def test_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("UNIFI_TOOL_REGISTRATION_MODE", "EAGER")
        assert validate_registration_mode(logging.getLogger("test")) == "eager"
