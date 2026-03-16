# Opt-in Delete Permissions Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make delete permissions opt-in via configuration instead of unconditionally denied, matching the existing create/update permission pattern.

**Architecture:** Remove the hardcoded delete block in `parse_permission()` and let delete flow through the existing priority chain (env var > config > default > fallback). Add `delete: false` to all config blocks for explicit denial. Fix two tools that use the `permission_action="update"` workaround.

**Tech Stack:** Python 3.13+, pytest, ruff

**Spec:** `docs/superpowers/specs/2026-03-16-opt-in-delete-permissions-design.md`

---

## Chunk 1: Core Permission Change + Tests

### Task 1: Write tests for delete permission behavior

**Files:**
- Create: `tests/unit/test_permissions.py`

- [ ] **Step 1: Write the test file**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_permissions.py -v`
Expected: Tests that expect delete to be allowed will FAIL because the hardcoded block at line 68-71 of `permissions.py` still returns `False` for all delete actions. Specifically these tests should fail:
- `test_delete_allowed_when_explicitly_true_in_category`
- `test_delete_falls_through_to_default_block`
- `test_delete_allowed_via_env_var`
- `test_env_var_overrides_config_for_delete`
- `test_delete_env_var_uses_category_map`

The "denied" tests and all `TestExistingPermissionsBehaviorUnchanged` tests should pass.

- [ ] **Step 3: Commit failing tests**

```bash
git add tests/unit/test_permissions.py
git commit -m "test: add delete permission tests (expected failures for #81)"
```

### Task 2: Remove hardcoded delete block + update docstring

**Files:**
- Modify: `src/utils/permissions.py:53,68-71`

- [ ] **Step 1: Remove the hardcoded delete block (lines 68-71)**

Remove these 4 lines from `parse_permission()`:

```python
    # Never allow delete operations regardless of configuration
    if action == "delete":
        logger.info(f"Delete operation requested for category '{category}'. All delete operations are disabled.")
        return False
```

- [ ] **Step 2: Update the docstring (line 53)**

Change line 53 from:
```
    4. Hardcoded default (read=true, delete=false, others=false)
```
to:
```
    4. Hardcoded fallback (read=true, all others=false)
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/unit/test_permissions.py -v`
Expected: ALL tests pass. Delete now flows through the normal chain.

- [ ] **Step 4: Run full test suite**

Run: `make test`
Expected: All existing tests pass (no other code depends on the delete block).

- [ ] **Step 5: Commit**

```bash
git add src/utils/permissions.py
git commit -m "feat: remove hardcoded delete denial, let delete flow through permission chain (#81)"
```

### Task 3: Add `delete: false` to all config categories

**Files:**
- Modify: `src/config/config.yaml:63-131`

- [ ] **Step 1: Add `delete: false` to every permissions block**

Update the `permissions:` section to add `delete: false` to the `default` block and all 16 category blocks:

```yaml
permissions:

  default:
    create: true
    update: true
    delete: false

  acl_rules:
    create: true
    update: true
    delete: false

  firewall_policies:
    create: true
    update: true
    delete: false

  traffic_routes:
    create: true
    update: true
    delete: false

  port_forwards:
    create: true
    update: true
    delete: false

  qos_rules:
    create: true
    update: true
    delete: false

  vpn_clients:
    create: true
    update: true
    delete: false

  networks:
    create: false  # Provisioning a new network can disrupt traffic
    update: false  # Changing subnets, VLANs, DHCP ranges requires care
    delete: false

  wlans:
    create: false
    update: false
    delete: false

  devices:
    create: false  # Adoption / provisioning – normally handled by controller, not tools
    update: false  # Firmware upgrade, rename, radio config, etc.
    delete: false

  clients:
    create: false  # Not applicable, but kept for symmetry
    update: false  # Block/unblock, rename, reconnect
    delete: false

  vpn_servers:
    create: false
    update: true
    delete: false

  events:
    create: false  # Events are read-only
    update: true   # Allow archiving alarms
    delete: false

  vouchers:
    create: true   # Allow creating guest vouchers
    update: true   # Allow revoking vouchers
    delete: false

  usergroups:
    create: true   # Allow creating bandwidth profiles
    update: true   # Allow modifying bandwidth limits
    delete: false

  routes:
    create: false  # Static routes can disrupt connectivity
    update: false  # Modifying routes requires careful planning
    delete: false

  snmp:
    create: false  # Not applicable
    update: true   # Allow enabling/disabling SNMP and changing community
    delete: false
```

- [ ] **Step 2: Run tests**

Run: `make test`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add src/config/config.yaml
git commit -m "config: add explicit delete: false to all permission categories (#81)"
```

---

## Chunk 2: Tool Permission Fixes + Cleanup

### Task 4: Fix `delete_acl_rule` permission action

**Files:**
- Modify: `src/tools/acl.py:234`

- [ ] **Step 1: Change permission_action from "update" to "delete"**

In the `@server.tool` decorator for `unifi_delete_acl_rule` (line 234), change:
```python
    permission_action="update",
```
to:
```python
    permission_action="delete",
```

- [ ] **Step 2: Run tests**

Run: `make test`
Expected: All tests pass.

- [ ] **Step 3: Commit**

```bash
git add src/tools/acl.py
git commit -m "fix: use permission_action='delete' for delete_acl_rule (#81)"
```

### Task 5: Fix `revoke_voucher` permission action + remove redundant inline checks

**Files:**
- Modify: `src/tools/hotspot.py:12,124-126,185,189-191`

- [ ] **Step 1: Change permission_action from "update" to "delete" on revoke_voucher**

In the `@server.tool` decorator for `unifi_revoke_voucher` (line 185), change:
```python
    permission_action="update",
```
to:
```python
    permission_action="delete",
```

- [ ] **Step 2: Remove redundant inline permission check in revoke_voucher**

Remove lines 189-191 from `revoke_voucher()`:
```python
    if not parse_permission(config.permissions, "voucher", "update"):
        logger.warning(f"Permission denied for revoking voucher ({voucher_id}).")
        return {"success": False, "error": "Permission denied to revoke vouchers."}
```

- [ ] **Step 3: Remove redundant inline permission check in create_voucher**

Remove lines 124-126 from `create_voucher()`:
```python
    if not parse_permission(config.permissions, "voucher", "create"):
        logger.warning("Permission denied for creating vouchers.")
        return {"success": False, "error": "Permission denied to create vouchers."}
```

- [ ] **Step 4: Remove unused import if parse_permission is no longer used**

Check if `parse_permission` is still imported elsewhere in the file. After removing both inline checks, the import at line 12 is no longer needed:
```python
# Remove this line:
from src.utils.permissions import parse_permission
```

Also remove `config` from the runtime import if it's no longer used in the file (line 10). Check if `config` is used elsewhere first — it's imported as `from src.runtime import config, server`. If `config` is only used in the removed permission checks, change to:
```python
from src.runtime import server
```

- [ ] **Step 5: Run linter and tests**

Run: `make pre-commit`
Expected: Format, lint, and all tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/tools/hotspot.py
git commit -m "fix: use permission_action='delete' for revoke_voucher, remove redundant inline checks (#81)"
```

---

## Chunk 3: Documentation Updates

### Task 6: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md:35,179`

- [ ] **Step 1: Update "Secure by default" definition (line 35)**

Change line 35 from:
```
- Delete operations are unconditionally denied at the permission layer
```
to:
```
- Delete operations are denied by default and require explicit opt-in via environment variable or config
```

- [ ] **Step 2: Update Permission Enforcement section (line 179)**

Change line 179 from:
```
- `delete` actions are **unconditionally denied** regardless of configuration
```
to:
```
- `delete` actions are **denied by default** and require explicit opt-in via `UNIFI_PERMISSIONS_<CATEGORY>_DELETE=true` or config
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md delete permission language (#81)"
```

### Task 7: Update .env.example

**Files:**
- Modify: `.env.example`

- [ ] **Step 1: Add delete permission examples**

Add the following at the end of the file (after the `UNIFI_MCP_ALLOWED_HOSTS` section):

```bash

# Optional: Permission overrides
# Delete permissions are denied by default. Enable per-category as needed.
# UNIFI_PERMISSIONS_ACL_RULES_DELETE="true"
# UNIFI_PERMISSIONS_VOUCHERS_DELETE="true"
# See docs/permissions.md for all available permission variables.
```

- [ ] **Step 2: Commit**

```bash
git add .env.example
git commit -m "docs: add delete permission examples to .env.example (#81)"
```

### Task 8: Update README.md permission section

**Files:**
- Modify: `README.md:759-813`

- [ ] **Step 1: Add delete to the env var examples**

In the "How to Enable Permissions" section (around line 779-792), add a delete example to each code block. In the Claude Desktop JSON example:
```json
"env": {
  "UNIFI_PERMISSIONS_NETWORKS_CREATE": "true",
  "UNIFI_PERMISSIONS_DEVICES_UPDATE": "true",
  "UNIFI_PERMISSIONS_ACL_RULES_DELETE": "true"
}
```

In the command line example:
```bash
export UNIFI_PERMISSIONS_NETWORKS_CREATE=true
export UNIFI_PERMISSIONS_DEVICES_UPDATE=true
export UNIFI_PERMISSIONS_ACL_RULES_DELETE=true
```

In the Docker example:
```bash
docker run -e UNIFI_PERMISSIONS_NETWORKS_CREATE=true -e UNIFI_PERMISSIONS_ACL_RULES_DELETE=true ...
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add delete permission examples to README (#81)"
```

### Task 9: Update docs/permissions.md

**Files:**
- Modify: `docs/permissions.md:236-243,167-178`

- [ ] **Step 1: Update Permission Actions table (around line 236-243)**

Change:
```markdown
| Action | Typical Operations |
|--------|-------------------|
| **create** | Add new resources (networks, rules, etc.) |
| **update** | Modify existing resources (rename, toggle, change config) |
| **delete** | Remove resources (typically uses "update" permission) |

Note: `delete` operations typically use the `update` permission since they modify the resource list.
```

to:
```markdown
| Action | Typical Operations | Default |
|--------|-------------------|---------|
| **create** | Add new resources (networks, rules, etc.) | Varies by category |
| **update** | Modify existing resources (rename, toggle, change config) | Varies by category |
| **delete** | Remove resources (ACL rules, vouchers, etc.) | Denied (opt-in) |
```

- [ ] **Step 2: Add Delete Variable column to Permission Variable Names table (around line 167-178)**

Add a `Delete Variable` column to the existing table:

```markdown
| Category | Create Variable | Update Variable | Delete Variable |
|----------|----------------|-----------------|-----------------|
| **networks** | `UNIFI_PERMISSIONS_NETWORKS_CREATE` | `UNIFI_PERMISSIONS_NETWORKS_UPDATE` | `UNIFI_PERMISSIONS_NETWORKS_DELETE` |
| **wlans** | `UNIFI_PERMISSIONS_WLANS_CREATE` | `UNIFI_PERMISSIONS_WLANS_UPDATE` | `UNIFI_PERMISSIONS_WLANS_DELETE` |
| **devices** | `UNIFI_PERMISSIONS_DEVICES_CREATE` | `UNIFI_PERMISSIONS_DEVICES_UPDATE` | `UNIFI_PERMISSIONS_DEVICES_DELETE` |
| **clients** | N/A | `UNIFI_PERMISSIONS_CLIENTS_UPDATE` | `UNIFI_PERMISSIONS_CLIENTS_DELETE` |
| **firewall_policies** | `UNIFI_PERMISSIONS_FIREWALL_POLICIES_CREATE` | `UNIFI_PERMISSIONS_FIREWALL_POLICIES_UPDATE` | `UNIFI_PERMISSIONS_FIREWALL_POLICIES_DELETE` |
| **traffic_routes** | `UNIFI_PERMISSIONS_TRAFFIC_ROUTES_CREATE` | `UNIFI_PERMISSIONS_TRAFFIC_ROUTES_UPDATE` | `UNIFI_PERMISSIONS_TRAFFIC_ROUTES_DELETE` |
| **port_forwards** | `UNIFI_PERMISSIONS_PORT_FORWARDS_CREATE` | `UNIFI_PERMISSIONS_PORT_FORWARDS_UPDATE` | `UNIFI_PERMISSIONS_PORT_FORWARDS_DELETE` |
| **qos_rules** | `UNIFI_PERMISSIONS_QOS_RULES_CREATE` | `UNIFI_PERMISSIONS_QOS_RULES_UPDATE` | `UNIFI_PERMISSIONS_QOS_RULES_DELETE` |
| **vpn_clients** | `UNIFI_PERMISSIONS_VPN_CLIENTS_CREATE` | `UNIFI_PERMISSIONS_VPN_CLIENTS_UPDATE` | `UNIFI_PERMISSIONS_VPN_CLIENTS_DELETE` |
| **vpn_servers** | `UNIFI_PERMISSIONS_VPN_SERVERS_CREATE` | `UNIFI_PERMISSIONS_VPN_SERVERS_UPDATE` | `UNIFI_PERMISSIONS_VPN_SERVERS_DELETE` |
| **acl_rules** | `UNIFI_PERMISSIONS_ACL_RULES_CREATE` | `UNIFI_PERMISSIONS_ACL_RULES_UPDATE` | `UNIFI_PERMISSIONS_ACL_RULES_DELETE` |
| **vouchers** | `UNIFI_PERMISSIONS_VOUCHERS_CREATE` | `UNIFI_PERMISSIONS_VOUCHERS_UPDATE` | `UNIFI_PERMISSIONS_VOUCHERS_DELETE` |
```

- [ ] **Step 3: Update Tools by Permission to include delete tools**

Add a new subsection after the ACL Rules section (or within it):

```markdown
### ACL Rules (Enabled by Default)
- ✅ `unifi_create_acl_rule`
- ✅ `unifi_update_acl_rule`
- ❌ `unifi_delete_acl_rule` (delete: disabled by default)
```

And update the Hotspot/Vouchers section:

```markdown
### Vouchers (Enabled by Default)
- ✅ `unifi_create_voucher`
- ❌ `unifi_revoke_voucher` (delete: disabled by default)
```

- [ ] **Step 4: Commit**

```bash
git add docs/permissions.md
git commit -m "docs: update permissions.md with delete as first-class action (#81)"
```

---

## Chunk 4: Final Verification

### Task 10: Run full quality gate

- [ ] **Step 1: Run pre-commit checks**

Run: `make pre-commit`
Expected: format + lint + test all pass.

- [ ] **Step 2: Verify delete denied by default**

Quick manual check: The test `test_delete_denied_by_hardcoded_fallback` already verifies this, but confirm the config also has `delete: false` everywhere:

Run: `grep -c "delete: false" src/config/config.yaml`
Expected: 17 (1 default + 16 categories)

- [ ] **Step 3: Verify no remaining `permission_action="update"` workarounds for delete tools**

Run: `grep -n 'permission_action="update"' src/tools/acl.py src/tools/hotspot.py`
Expected: Only `update_acl_rule` in acl.py should show. `delete_acl_rule` and `revoke_voucher` should now use `"delete"`.
