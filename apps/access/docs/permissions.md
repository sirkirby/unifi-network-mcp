# Permission System

Permissions control which mutating tools are available. All mutations are disabled by default; read-only tools are always available.

## How It Works

1. Each mutating tool declares a **category** and **action** (create, update, or delete)
2. At startup, the server checks permission config for that category/action
3. Denied tools are **not registered** with the MCP server -- they cannot be called
4. All tools remain discoverable via `access_tool_index` regardless of permission status

## Priority Order

1. **Environment variables** (highest) -- `UNIFI_PERMISSIONS_<CATEGORY>_<ACTION>=true`
2. **Config YAML** -- `permissions.<category>.<action>` in `config.yaml`
3. **Default section** -- `permissions.default.<action>` in `config.yaml`
4. **Hardcoded fallback** -- `read: true`, `delete: false`

## Category Defaults

All mutation categories default to **disabled** for Access. This is conservative because Access operations control physical security hardware -- doors, locks, and credential assignments.

| Category | Create | Update | Delete | Rationale |
|----------|--------|--------|--------|-----------|
| `doors` | -- | no | -- | Lock/unlock controls physical door state |
| `policies` | -- | no | -- | Policy changes affect who can enter |
| `credentials` | no | -- | no | Creates/revokes physical access tokens |
| `visitors` | no | -- | no | Creates/removes time-bounded visitor access |
| `events` | -- | -- | -- | Events are system-generated (read-only) |
| `devices` | -- | no | -- | Reboot interrupts access control hardware |
| `system` | -- | -- | -- | System info is read-only |

**Note:** Read-only tools (list, get, status, schedules) are always available and require no permission configuration.

## Enabling Permissions

### Environment Variables (Recommended)

```bash
# Enable door lock/unlock
export UNIFI_PERMISSIONS_DOORS_UPDATE=true

# Enable credential creation and revocation
export UNIFI_PERMISSIONS_CREDENTIALS_CREATE=true
export UNIFI_PERMISSIONS_CREDENTIALS_DELETE=true

# Enable visitor pass management
export UNIFI_PERMISSIONS_VISITORS_CREATE=true
export UNIFI_PERMISSIONS_VISITORS_DELETE=true

# Enable policy updates
export UNIFI_PERMISSIONS_POLICIES_UPDATE=true

# Enable device reboot
export UNIFI_PERMISSIONS_DEVICES_UPDATE=true
```

For Claude Desktop, add to the `env` section:
```json
{
  "env": {
    "UNIFI_PERMISSIONS_DOORS_UPDATE": "true",
    "UNIFI_PERMISSIONS_CREDENTIALS_CREATE": "true"
  }
}
```

For Docker:
```bash
docker run -e UNIFI_PERMISSIONS_DOORS_UPDATE=true ...
```

Accepted values: `true`, `1`, `yes`, `on` (case-insensitive).

### Config File

Edit `src/unifi_access_mcp/config/config.yaml`:

```yaml
permissions:
  doors:
    update: true
  credentials:
    create: true
    delete: true
```

Then restart the server. No manifest rebuild is needed for permission changes.

## All Permission Variables

| Category | Create | Update | Delete |
|----------|--------|--------|--------|
| doors | `UNIFI_PERMISSIONS_DOORS_CREATE` | `UNIFI_PERMISSIONS_DOORS_UPDATE` | `UNIFI_PERMISSIONS_DOORS_DELETE` |
| policies | `UNIFI_PERMISSIONS_POLICIES_CREATE` | `UNIFI_PERMISSIONS_POLICIES_UPDATE` | `UNIFI_PERMISSIONS_POLICIES_DELETE` |
| credentials | `UNIFI_PERMISSIONS_CREDENTIALS_CREATE` | `UNIFI_PERMISSIONS_CREDENTIALS_UPDATE` | `UNIFI_PERMISSIONS_CREDENTIALS_DELETE` |
| visitors | `UNIFI_PERMISSIONS_VISITORS_CREATE` | `UNIFI_PERMISSIONS_VISITORS_UPDATE` | `UNIFI_PERMISSIONS_VISITORS_DELETE` |
| events | `UNIFI_PERMISSIONS_EVENTS_CREATE` | `UNIFI_PERMISSIONS_EVENTS_UPDATE` | `UNIFI_PERMISSIONS_EVENTS_DELETE` |
| devices | `UNIFI_PERMISSIONS_DEVICES_CREATE` | `UNIFI_PERMISSIONS_DEVICES_UPDATE` | `UNIFI_PERMISSIONS_DEVICES_DELETE` |
| system | `UNIFI_PERMISSIONS_SYSTEM_CREATE` | `UNIFI_PERMISSIONS_SYSTEM_UPDATE` | `UNIFI_PERMISSIONS_SYSTEM_DELETE` |

## Tools Affected by Permissions

| Tool | Category | Action | What it does |
|------|----------|--------|-------------|
| `access_unlock_door` | doors | update | Unlock a door for a specified duration |
| `access_lock_door` | doors | update | Lock a door immediately |
| `access_update_policy` | policies | update | Update policy name, doors, schedule, user groups |
| `access_create_credential` | credentials | create | Create NFC card, PIN, or mobile credential |
| `access_revoke_credential` | credentials | delete | Permanently revoke a credential |
| `access_create_visitor` | visitors | create | Create a time-bounded visitor pass |
| `access_delete_visitor` | visitors | delete | Permanently remove a visitor pass |
| `access_reboot_device` | devices | update | Reboot an access hub, reader, relay, or intercom |

## Behavior by Registration Mode

| Mode | Denied tool visible? | Denied tool callable? |
|------|---------------------|----------------------|
| **eager** | Not in client tool list | No |
| **lazy** | In `access_tool_index` | No (returns permission error) |
| **meta_only** | In `access_tool_index` | No (returns permission error) |

If a tool you expect is missing from your client's tool list, the most common cause is a disabled permission.

## Confirmation System

All mutating tools use a **preview-then-confirm** pattern:

1. Call without `confirm` (default) -- returns a preview of the change
2. Call with `confirm=true` -- executes the mutation

Set `UNIFI_AUTO_CONFIRM=true` to skip previews for automation workflows (n8n, Make, Zapier).

| Level | Method | Use Case |
|-------|--------|----------|
| Per-call | `confirm=true` in arguments | LLM explicitly confirms |
| Per-session | System prompt instructs auto-confirm | Agent follows standing instructions |
| Per-environment | `UNIFI_AUTO_CONFIRM=true` | Workflow automation |
