"""Tests for the shared PermissionChecker class."""

import os
from unittest.mock import patch

import pytest

from unifi_mcp_shared.permissions import PermissionChecker


class TestPermissionCheckerWithCustomCategoryMap:
    """Category map is injected, not hardcoded."""

    def test_check_allowed_action(self):
        category_map = {"my_category": "my_config_key"}
        permissions_config = {"my_config_key": {"read": True, "create": False}}
        checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
        assert checker.check("my_category", "read") is True

    def test_check_denied_action(self):
        category_map = {"my_category": "my_config_key"}
        permissions_config = {"my_config_key": {"read": True, "create": False}}
        checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
        assert checker.check("my_category", "create") is False


class TestPermissionCheckerEnvVarOverride:
    """Env vars take priority over config."""

    def test_env_var_overrides_false_to_true(self, monkeypatch):
        category_map = {"firewall": "firewall_policies"}
        permissions_config = {"firewall_policies": {"create": False}}
        checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
        monkeypatch.setenv("UNIFI_PERMISSIONS_FIREWALL_POLICIES_CREATE", "true")
        assert checker.check("firewall", "create") is True

    def test_env_var_overrides_true_to_false(self, monkeypatch):
        category_map = {"firewall": "firewall_policies"}
        permissions_config = {"firewall_policies": {"create": True}}
        checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
        monkeypatch.setenv("UNIFI_PERMISSIONS_FIREWALL_POLICIES_CREATE", "false")
        assert checker.check("firewall", "create") is False

    def test_env_var_accepts_1_as_true(self, monkeypatch):
        category_map = {"firewall": "firewall_policies"}
        permissions_config = {"firewall_policies": {"create": False}}
        checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
        monkeypatch.setenv("UNIFI_PERMISSIONS_FIREWALL_POLICIES_CREATE", "1")
        assert checker.check("firewall", "create") is True

    def test_env_var_accepts_yes_as_true(self, monkeypatch):
        category_map = {"firewall": "firewall_policies"}
        permissions_config = {"firewall_policies": {"create": False}}
        checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
        monkeypatch.setenv("UNIFI_PERMISSIONS_FIREWALL_POLICIES_CREATE", "yes")
        assert checker.check("firewall", "create") is True

    def test_env_var_accepts_on_as_true(self, monkeypatch):
        category_map = {"firewall": "firewall_policies"}
        permissions_config = {"firewall_policies": {"create": False}}
        checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
        monkeypatch.setenv("UNIFI_PERMISSIONS_FIREWALL_POLICIES_CREATE", "on")
        assert checker.check("firewall", "create") is True


class TestPermissionCheckerDefaultFallback:
    """Falls back to default section when category not configured."""

    def test_falls_back_to_default_read(self):
        category_map = {"unknown": "unknown_category"}
        permissions_config = {"default": {"read": True, "create": False}}
        checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
        assert checker.check("unknown", "read") is True

    def test_falls_back_to_default_create(self):
        category_map = {"unknown": "unknown_category"}
        permissions_config = {"default": {"read": True, "create": False}}
        checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
        assert checker.check("unknown", "create") is False


class TestPermissionCheckerHardcodedDefaults:
    """Hardcoded fallback when nothing is configured."""

    def test_read_default_true(self):
        checker = PermissionChecker(category_map={}, permissions={})
        assert checker.check("anything", "read") is True

    def test_delete_default_false(self):
        checker = PermissionChecker(category_map={}, permissions={})
        assert checker.check("anything", "delete") is False

    def test_create_default_false(self):
        checker = PermissionChecker(category_map={}, permissions={})
        assert checker.check("anything", "create") is False

    def test_update_default_false(self):
        checker = PermissionChecker(category_map={}, permissions={})
        assert checker.check("anything", "update") is False


class TestPermissionCheckerNonePermissions:
    """Handles None permissions gracefully."""

    def test_none_permissions_read_allowed(self):
        checker = PermissionChecker(category_map={}, permissions=None)
        assert checker.check("anything", "read") is True

    def test_none_permissions_create_denied(self):
        checker = PermissionChecker(category_map={}, permissions=None)
        assert checker.check("anything", "create") is False


class TestPermissionCheckerCategoryMapPassthrough:
    """When category is not in the map, use it as-is."""

    def test_unmapped_category_uses_raw_key(self):
        category_map = {}
        permissions_config = {"my_raw_category": {"read": True, "create": True}}
        checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
        assert checker.check("my_raw_category", "create") is True

    def test_mapped_category_uses_config_key(self):
        category_map = {"fw": "firewall_policies"}
        permissions_config = {"firewall_policies": {"create": True}}
        checker = PermissionChecker(category_map=category_map, permissions=permissions_config)
        assert checker.check("fw", "create") is True


class TestPermissionCheckerDeleteBehavior:
    """Delete action specific tests matching existing network app tests."""

    def test_delete_denied_by_default_empty_permissions(self):
        checker = PermissionChecker(category_map={}, permissions={})
        assert checker.check("acl_rules", "delete") is False

    def test_delete_allowed_when_explicitly_true(self):
        checker = PermissionChecker(
            category_map={},
            permissions={"acl_rules": {"delete": True}},
        )
        assert checker.check("acl_rules", "delete") is True

    def test_delete_denied_when_explicitly_false(self):
        checker = PermissionChecker(
            category_map={},
            permissions={"acl_rules": {"delete": False}},
        )
        assert checker.check("acl_rules", "delete") is False

    def test_delete_falls_through_to_default(self):
        checker = PermissionChecker(
            category_map={},
            permissions={
                "default": {"delete": True},
                "acl_rules": {"create": True},
            },
        )
        assert checker.check("acl_rules", "delete") is True

    def test_env_var_overrides_delete(self, monkeypatch):
        checker = PermissionChecker(
            category_map={},
            permissions={"acl_rules": {"delete": False}},
        )
        monkeypatch.setenv("UNIFI_PERMISSIONS_ACL_RULES_DELETE", "true")
        assert checker.check("acl_rules", "delete") is True
