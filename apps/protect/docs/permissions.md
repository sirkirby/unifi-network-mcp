# Permission System — Protect Server

All tools are always visible and discoverable. Authorization happens at call time through two concepts: **Permission Mode** and **Policy Gates**.

## Permission Mode

Controls how the server handles mutating tool calls globally.

| Variable | Scope | Values | Default |
|----------|-------|--------|---------|
| `UNIFI_TOOL_PERMISSION_MODE` | All servers | `confirm`, `bypass` | `confirm` |
| `UNIFI_PROTECT_TOOL_PERMISSION_MODE` | Protect only | `confirm`, `bypass` | inherits global |

- **`confirm`** (default) — mutating tools require the preview-then-confirm flow before executing
- **`bypass`** — skips confirmation for all mutations; intended for automation workflows

The server-specific variable takes priority over the global one.

## Policy Gates

Fine-grained authorization over which mutations are permitted. Most specific rule wins.

| Specificity | Pattern | Example |
|-------------|---------|---------|
| Global action | `UNIFI_POLICY_<ACTION>` | `UNIFI_POLICY_DELETE=false` |
| Server + action | `UNIFI_POLICY_PROTECT_<ACTION>` | `UNIFI_POLICY_PROTECT_UPDATE=true` |
| Server + category + action | `UNIFI_POLICY_PROTECT_<CATEGORY>_<ACTION>` | `UNIFI_POLICY_PROTECT_CAMERAS_UPDATE=true` |

Actions: `CREATE`, `UPDATE`, `DELETE`

Accepted values: `true`, `1`, `yes`, `on` (case-insensitive). Unset means the next less-specific rule applies.

## Protect Categories

Protect defaults all mutations to denied because operations directly affect physical security hardware.

| Category | Create | Update | Delete | Notes |
|----------|--------|--------|--------|-------|
| `alarm` | — | `UNIFI_POLICY_PROTECT_ALARM_UPDATE` | — | Arm/disarm Alarm Manager profiles |
| `cameras` | — | `UNIFI_POLICY_PROTECT_CAMERAS_UPDATE` | — | IR, HDR, recording, PTZ, reboot |
| `chimes` | — | `UNIFI_POLICY_PROTECT_CHIMES_UPDATE` | — | Volume, repeat, trigger |
| `events` | — | `UNIFI_POLICY_PROTECT_EVENTS_UPDATE` | — | Acknowledge/favorite |
| `lights` | — | `UNIFI_POLICY_PROTECT_LIGHTS_UPDATE` | — | Brightness, sensitivity, duration |
| `liveviews` | `UNIFI_POLICY_PROTECT_LIVEVIEWS_CREATE` | — | `UNIFI_POLICY_PROTECT_LIVEVIEWS_DELETE` | Not supported by uiprotect API |
| `recordings` | — | — | `UNIFI_POLICY_PROTECT_RECORDINGS_DELETE` | Not supported by API |
| `sensors` | — | `UNIFI_POLICY_PROTECT_SENSORS_UPDATE` | — | Hardware devices |
| `system` | — | `UNIFI_POLICY_PROTECT_SYSTEM_UPDATE` | — | NVR system settings |

Read-only tools (list, get, snapshots, streams, analytics) are always available with no policy configuration required.

## Common Scenarios

### Zero config (default)

No configuration needed. All tools work — reads execute immediately, mutations require confirmation (preview-then-confirm). This is the safest default.

### Restrict to camera and device control only

```bash
UNIFI_POLICY_PROTECT_CREATE=false
UNIFI_POLICY_PROTECT_UPDATE=false
UNIFI_POLICY_PROTECT_DELETE=false
UNIFI_POLICY_PROTECT_CAMERAS_UPDATE=true
UNIFI_POLICY_PROTECT_LIGHTS_UPDATE=true
UNIFI_POLICY_PROTECT_CHIMES_UPDATE=true
```

### Lock down deletes and creates

```bash
UNIFI_POLICY_PROTECT_DELETE=false
UNIFI_POLICY_PROTECT_CREATE=false
```

### Full bypass for automation

```bash
UNIFI_PROTECT_TOOL_PERMISSION_MODE=bypass
UNIFI_POLICY_PROTECT_UPDATE=true
```

### Claude Desktop example

```json
{
  "env": {
    "UNIFI_POLICY_PROTECT_CAMERAS_UPDATE": "true",
    "UNIFI_POLICY_PROTECT_LIGHTS_UPDATE": "true"
  }
}
```

## Confirmation Flow

When `UNIFI_PROTECT_TOOL_PERMISSION_MODE=confirm` (default), mutating tools follow a two-step pattern:

1. Call without `confirm` — returns a preview of the change, no mutation occurs
2. Call with `confirm=true` — executes the mutation

This applies even when a policy gate permits the action.

## Backwards Compatibility

The following deprecated variables are still accepted but will be removed in a future release:

| Deprecated | Equivalent |
|------------|-----------|
| `UNIFI_AUTO_CONFIRM=true` | `UNIFI_TOOL_PERMISSION_MODE=bypass` |
| `UNIFI_PERMISSIONS_<CAT>_<ACTION>=true` | `UNIFI_POLICY_PROTECT_<CAT>_<ACTION>=true` |

Deprecated variables are resolved before new-style variables and have lower priority if both are set.
