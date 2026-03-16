"""Tests for parse_permission delete action handling."""

import os
from unittest.mock import patch

import pytest

from src.utils.permissions import parse_permission


class TestDeletePermissions:
    """Tests for delete action flowing through the normal permission chain."""

    def test_delete_denied_by_default_empty_permissions(self):
        """Delete is denied when permissions dict is empty."""
        assert parse_permission({}, "acl_rules", "delete") is False

    def test_delete_denied_by_default_none_permissions(self):
        """Delete is denied when permissions is None."""
        assert parse_permission(None, "acl_rules", "delete") is False

    def test_delete_denied_when_explicitly_false_in_category(self):
        """Delete is denied when category explicitly sets delete: false."""
        permissions = {"acl_rules": {"create": True, "update": True, "delete": False}}
        assert parse_permission(permissions, "acl_rules", "delete") is False

    def test_delete_allowed_when_explicitly_true_in_category(self):
        """Delete is allowed when category explicitly sets delete: true."""
        permissions = {"acl_rules": {"create": True, "update": True, "delete": True}}
        assert parse_permission(permissions, "acl_rules", "delete") is True

    def test_delete_falls_through_to_default_block(self):
        """Delete uses default block when category has no delete entry."""
        permissions = {
            "default": {"create": True, "update": True, "delete": True},
            "acl_rules": {"create": True, "update": True},
        }
        assert parse_permission(permissions, "acl_rules", "delete") is True

    def test_delete_denied_by_default_block(self):
        """Delete is denied when default block sets delete: false."""
        permissions = {
            "default": {"create": True, "update": True, "delete": False},
            "acl_rules": {"create": True, "update": True},
        }
        assert parse_permission(permissions, "acl_rules", "delete") is False

    def test_delete_denied_by_hardcoded_fallback(self):
        """Delete is denied by the hardcoded fallback when no config exists."""
        permissions = {"acl_rules": {"create": True, "update": True}}
        assert parse_permission(permissions, "acl_rules", "delete") is False

    @patch.dict(os.environ, {"UNIFI_PERMISSIONS_ACL_RULES_DELETE": "true"})
    def test_delete_allowed_via_env_var(self):
        """Delete is allowed when env var is set to true."""
        permissions = {"acl_rules": {"delete": False}}
        assert parse_permission(permissions, "acl_rules", "delete") is True

    @patch.dict(os.environ, {"UNIFI_PERMISSIONS_ACL_RULES_DELETE": "false"})
    def test_delete_denied_via_env_var(self):
        """Delete is denied when env var is set to false."""
        permissions = {"acl_rules": {"delete": True}}
        assert parse_permission(permissions, "acl_rules", "delete") is False

    @patch.dict(os.environ, {"UNIFI_PERMISSIONS_ACL_RULES_DELETE": "true"})
    def test_env_var_overrides_config_for_delete(self):
        """Env var takes priority over config for delete."""
        permissions = {
            "default": {"delete": False},
            "acl_rules": {"delete": False},
        }
        assert parse_permission(permissions, "acl_rules", "delete") is True

    @patch.dict(os.environ, {"UNIFI_PERMISSIONS_VOUCHERS_DELETE": "true"})
    def test_delete_env_var_uses_category_map(self):
        """Env var works with CATEGORY_MAP shorthand (voucher -> vouchers)."""
        permissions = {"vouchers": {"delete": False}}
        assert parse_permission(permissions, "voucher", "delete") is True


class TestExistingPermissionsBehaviorUnchanged:
    """Verify existing create/update/read behavior is not affected."""

    def test_read_allowed_by_default(self):
        """Read is still allowed by default when not configured."""
        assert parse_permission({}, "acl_rules", "read") is True

    def test_create_denied_by_hardcoded_fallback(self):
        """Create is still denied when no config exists (non-read fallback)."""
        assert parse_permission({"acl_rules": {}}, "acl_rules", "create") is False

    def test_create_allowed_by_config(self):
        """Create is still allowed when config says true."""
        permissions = {"acl_rules": {"create": True}}
        assert parse_permission(permissions, "acl_rules", "create") is True

    @patch.dict(os.environ, {"UNIFI_PERMISSIONS_NETWORKS_CREATE": "true"})
    def test_create_env_var_still_works(self):
        """Create env var override still works."""
        permissions = {"networks": {"create": False}}
        assert parse_permission(permissions, "network", "create") is True
