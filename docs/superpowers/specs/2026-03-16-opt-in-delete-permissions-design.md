# Opt-in Delete Permissions

**Issue:** [#81](https://github.com/sirkirby/unifi-network-mcp/issues/81)
**Date:** 2026-03-16
**Status:** Draft

## Problem

The permission system hardcodes an unconditional denial for all `delete` actions in `src/utils/permissions.py` (lines 68-71), bypassing the normal priority chain. This forces tools that perform destructive operations (`delete_acl_rule`, `revoke_voucher`) to use `permission_action="update"` as a workaround, conflating delete and update permissions.

## Solution

Remove the hardcoded delete block and let delete flow through the existing permission resolution chain:

1. **Environment variable**: `UNIFI_PERMISSIONS_<CATEGORY>_DELETE=true`
2. **Config file**: `permissions.<category>.delete: true`
3. **Config default**: `permissions.default.delete: true`
4. **Hardcoded fallback**: `false` (the final fallback at line 105-117 already denies non-read actions)

Delete remains **denied by default** but becomes **opt-in via configuration** — matching the existing pattern for create/update.

## Changes

### 1. `src/utils/permissions.py` — Remove hardcoded delete block + update docstring

Remove lines 68-71:

```python
# REMOVE:
if action == "delete":
    logger.info(f"Delete operation requested for category '{category}'. All delete operations are disabled.")
    return False
```

The existing resolution chain already handles delete correctly:
- Env var override (line 73-83) → config category (line 90-96) → config default (line 98-103) → final fallback denies non-read (line 105-117)

Also update the docstring at line 53. Change:
```
4. Hardcoded default (read=true, delete=false, others=false)
```
to:
```
4. Hardcoded fallback (read=true, all others=false)
```

### 2. `src/config/config.yaml` — Add explicit `delete: false` to all category blocks

Add `delete: false` to the `default:` block and all 16 existing category blocks. This makes the denial explicit in config rather than relying solely on the hardcoded fallback, consistent with how create/update are handled.

Categories to update (all existing blocks):
- `default`
- `acl_rules`
- `firewall_policies`
- `traffic_routes`
- `port_forwards`
- `qos_rules`
- `vpn_clients`
- `networks`
- `wlans`
- `devices`
- `clients`
- `vpn_servers`
- `events`
- `vouchers`
- `usergroups`
- `routes`
- `snmp`

Example:
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
```

### 3. `src/tools/acl.py` — Fix `delete_acl_rule` permission action

Change `permission_action="update"` to `permission_action="delete"` on the `unifi_delete_acl_rule` tool decorator (line 234).

### 4. `src/tools/hotspot.py` — Fix `revoke_voucher` permission action + cleanup redundant inline checks

**Permission fix:** Change `permission_action="update"` to `permission_action="delete"` on the `unifi_revoke_voucher` tool decorator (line 185).

**Cleanup — `revoke_voucher`:** Remove the redundant inline `parse_permission()` check at lines 189-191. The `permissioned_tool` decorator already enforces permissions at registration time — this inline check duplicates the decorator's work.

**Cleanup — `create_voucher`:** Remove the redundant inline `parse_permission()` check at lines 124-126. Same issue — the decorator at line 111 (`permission_action="create"`) already handles this.

### 5. `tests/unit/test_permissions.py` — New test file

Test `parse_permission()` for delete actions:

| Test case | Setup | Expected |
|-----------|-------|----------|
| Delete denied by default (no config) | Empty permissions dict | `False` |
| Delete denied when explicitly `false` in config | `permissions.acl_rules.delete: false` | `False` |
| Delete allowed when explicitly `true` in config | `permissions.acl_rules.delete: true` | `True` |
| Delete allowed via env var override | `UNIFI_PERMISSIONS_ACL_RULES_DELETE=true` | `True` |
| Delete denied via env var override | `UNIFI_PERMISSIONS_ACL_RULES_DELETE=false` | `False` |
| Delete falls through to default block | `permissions.default.delete: true`, no category entry | `True` |
| Env var overrides config for delete | Config `false`, env var `true` | `True` |

### 6. Documentation updates

**`CLAUDE.md`** (line 18): Change "Delete always denied" to "Delete denied by default, opt-in via config/env var".

Note: `CLAUDE.md` references `oak/constitution.md` as the single source of truth, but that file does not currently exist on disk. The authoritative content lives in `CLAUDE.md` itself. If `oak/constitution.md` is created in the future, it would need the same updates.

**`.env.example`**: Add commented examples:
```bash
# Optional: Enable delete permissions (denied by default)
# UNIFI_PERMISSIONS_ACL_RULES_DELETE="true"
# UNIFI_PERMISSIONS_VOUCHERS_DELETE="true"
```

**`README.md`** (Permission System section): Add delete to the env var examples and note that delete permissions follow the same pattern as create/update.

**`docs/permissions.md`**:
- Update Permission Actions table (line 236-241) to show delete as a proper first-class action
- Remove the note "delete operations typically use the update permission" (line 243)
- Add `Delete Variable` column to the Permission Variable Names table (line 167-178)
- Update Tools by Permission section to show delete tools (`unifi_delete_acl_rule`, `unifi_revoke_voucher`) with their proper permission

## What stays the same

- The permission priority chain logic — untouched
- The `permissioned_tool` decorator — untouched
- The confirmation system — untouched
- All other tool permission annotations — untouched
- The `CATEGORY_MAP` in permissions.py — untouched (already maps `"acl"` → `"acl_rules"` and `"voucher"` → `"vouchers"`)

## Verification

1. `make pre-commit` passes (format + lint + test)
2. Delete tools denied by default with no config changes
3. Delete tools enabled when `UNIFI_PERMISSIONS_<CAT>_DELETE=true` is set
4. `revoke_voucher` and `delete_acl_rule` use proper `permission_action="delete"`
5. No behavioral change for existing create/update permissions
