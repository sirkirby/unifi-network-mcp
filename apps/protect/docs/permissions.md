# Permission System

Permissions control which mutating tools are available. All mutations are disabled by default; read-only tools are always available.

## How It Works

1. Each mutating tool declares a **category** and **action** (create, update, or delete)
2. At startup, the server checks permission config for that category/action
3. Denied tools are **not registered** with the MCP server -- they cannot be called
4. All tools remain discoverable via `protect_tool_index` regardless of permission status

## Priority Order

1. **Environment variables** (highest) -- `UNIFI_PERMISSIONS_<CATEGORY>_<ACTION>=true`
2. **Config YAML** -- `permissions.<category>.<action>` in `config.yaml`
3. **Default section** -- `permissions.default.<action>` in `config.yaml`
4. **Hardcoded fallback** -- `read: true`, `delete: false`

## Category Defaults

All mutation categories default to **disabled** for Protect. This is more conservative than the Network server because Protect operations directly affect physical security hardware.

| Category | Create | Update | Delete | Rationale |
|----------|--------|--------|--------|-----------|
| `cameras` | no | no | no | Settings affect recording, IR, HDR; reboot interrupts feeds |
| `events` | no | no | no | Events are system-generated; acknowledge is an update |
| `recordings` | no | no | no | NVR manages retention; deletion not supported by API |
| `lights` | no | no | no | Controls physical floodlights |
| `sensors` | no | no | no | Hardware devices, not user-created |
| `chimes` | no | no | no | Controls audible devices |
| `liveviews` | no | no | no | Create/delete not supported by uiprotect API |
| `system` | no | no | no | System settings are sensitive |

**Note:** Read-only tools (list, get, status, analytics) are always available and require no permission configuration.

## Enabling Permissions

### Environment Variables (Recommended)

```bash
# Enable camera settings updates (IR, HDR, recording toggle, PTZ, reboot)
export UNIFI_PERMISSIONS_CAMERAS_UPDATE=true

# Enable light control
export UNIFI_PERMISSIONS_LIGHTS_UPDATE=true

# Enable chime control (settings + trigger)
export UNIFI_PERMISSIONS_CHIMES_UPDATE=true

# Enable event acknowledgment
export UNIFI_PERMISSIONS_EVENTS_UPDATE=true
```

For Claude Desktop, add to the `env` section:
```json
{
  "env": {
    "UNIFI_PERMISSIONS_CAMERAS_UPDATE": "true",
    "UNIFI_PERMISSIONS_LIGHTS_UPDATE": "true"
  }
}
```

For Docker:
```bash
docker run -e UNIFI_PERMISSIONS_CAMERAS_UPDATE=true ...
```

Accepted values: `true`, `1`, `yes`, `on` (case-insensitive).

### Config File

Edit `src/unifi_protect_mcp/config/config.yaml`:

```yaml
permissions:
  cameras:
    update: true
  lights:
    update: true
```

Then restart the server. No manifest rebuild is needed for permission changes.

## All Permission Variables

| Category | Create | Update | Delete |
|----------|--------|--------|--------|
| cameras | `UNIFI_PERMISSIONS_CAMERAS_CREATE` | `UNIFI_PERMISSIONS_CAMERAS_UPDATE` | `UNIFI_PERMISSIONS_CAMERAS_DELETE` |
| events | `UNIFI_PERMISSIONS_EVENTS_CREATE` | `UNIFI_PERMISSIONS_EVENTS_UPDATE` | `UNIFI_PERMISSIONS_EVENTS_DELETE` |
| recordings | `UNIFI_PERMISSIONS_RECORDINGS_CREATE` | `UNIFI_PERMISSIONS_RECORDINGS_UPDATE` | `UNIFI_PERMISSIONS_RECORDINGS_DELETE` |
| lights | `UNIFI_PERMISSIONS_LIGHTS_CREATE` | `UNIFI_PERMISSIONS_LIGHTS_UPDATE` | `UNIFI_PERMISSIONS_LIGHTS_DELETE` |
| sensors | `UNIFI_PERMISSIONS_SENSORS_CREATE` | `UNIFI_PERMISSIONS_SENSORS_UPDATE` | `UNIFI_PERMISSIONS_SENSORS_DELETE` |
| chimes | `UNIFI_PERMISSIONS_CHIMES_CREATE` | `UNIFI_PERMISSIONS_CHIMES_UPDATE` | `UNIFI_PERMISSIONS_CHIMES_DELETE` |
| liveviews | `UNIFI_PERMISSIONS_LIVEVIEWS_CREATE` | `UNIFI_PERMISSIONS_LIVEVIEWS_UPDATE` | `UNIFI_PERMISSIONS_LIVEVIEWS_DELETE` |
| system | `UNIFI_PERMISSIONS_SYSTEM_CREATE` | `UNIFI_PERMISSIONS_SYSTEM_UPDATE` | `UNIFI_PERMISSIONS_SYSTEM_DELETE` |

## Tools Affected by Permissions

| Tool | Category | Action | What it does |
|------|----------|--------|-------------|
| `protect_update_camera_settings` | cameras | update | Change IR, HDR, mic, speaker, status light, motion detection |
| `protect_toggle_recording` | cameras | update | Enable/disable camera recording |
| `protect_ptz_move` | cameras | update | Adjust PTZ camera zoom |
| `protect_ptz_preset` | cameras | update | Move PTZ camera to preset position |
| `protect_reboot_camera` | cameras | update | Reboot a camera (interrupts recordings) |
| `protect_acknowledge_event` | events | update | Mark event as favorite (acknowledge) |
| `protect_delete_recording` | recordings | delete | Recording deletion (not supported by API) |
| `protect_update_light` | lights | update | Change brightness, sensitivity, duration |
| `protect_update_chime` | chimes | update | Change volume, repeat times |
| `protect_trigger_chime` | chimes | update | Play chime tone |
| `protect_create_liveview` | liveviews | create | Liveview creation (not supported by API) |
| `protect_delete_liveview` | liveviews | delete | Liveview deletion (not supported by API) |

## Behavior by Registration Mode

| Mode | Denied tool visible? | Denied tool callable? |
|------|---------------------|----------------------|
| **eager** | Not in client tool list | No |
| **lazy** | In `protect_tool_index` | No (returns permission error) |
| **meta_only** | In `protect_tool_index` | No (returns permission error) |

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
