---
name: unifi-access
description: How to manage UniFi Access door control — locks, credentials, visitors, access policies, and events. Use this skill when the user mentions UniFi Access, door locks, door access, building access, NFC cards, PIN codes, visitor passes, access policies, access schedules, door readers, or any UniFi Access task.
---

# UniFi Access MCP Server

You have access to a UniFi Access MCP server that lets you query and manage a UniFi Access controller. It provides 29 tools covering doors, locks, credentials, visitors, access policies, and events.

## Tool Discovery

The server uses **lazy loading** by default — only meta-tools are registered initially:

| Meta-Tool | Purpose |
|-----------|---------|
| `access_tool_index` | List all 29 tools with full parameter schemas |
| `access_execute` | Call any tool by name (essential in lazy mode) |
| `access_batch` | Run multiple tools in parallel |
| `access_batch_status` | Check async batch job status |

**Workflow:** Call `access_tool_index` to find the right tool, then `access_execute` to call it. Use `access_batch` for multiple independent queries.

## Safety Model

**All mutations are disabled by default** because Access controls physical door locks and building entry.

**Read operations** — always available. Listing doors, events, users, credentials — all work without permissions.

**Mutations** require explicit opt-in via env vars:
- `UNIFI_PERMISSIONS_DOORS_UPDATE=true` — lock/unlock doors
- `UNIFI_PERMISSIONS_CREDENTIALS_CREATE=true` — create NFC/PIN/mobile credentials
- `UNIFI_PERMISSIONS_CREDENTIALS_DELETE=true` — revoke credentials
- `UNIFI_PERMISSIONS_VISITORS_CREATE=true` — create visitor passes
- `UNIFI_PERMISSIONS_VISITORS_DELETE=true` — delete visitor passes
- `UNIFI_PERMISSIONS_POLICIES_UPDATE=true` — update access policies
- `UNIFI_PERMISSIONS_DEVICES_UPDATE=true` — reboot devices

**Confirmation flow** — every mutation uses preview-then-confirm:
1. Default call → returns preview of what would change
2. Call with `confirm=true` → executes the mutation

Door lock/unlock operations are **physical real-world actions** — always preview first.

## Response Format

All tools return: `{"success": true, "data": ...}`, `{"success": false, "error": "..."}`, or `{"success": true, "requires_confirmation": true, "preview": ...}`. Always check `success` first.

## Key Capabilities

- **Door control:** `access_lock_door` / `access_unlock_door` — unlock relocks automatically after duration (default 2 seconds)
- **Real-time events:** `access_recent_events` reads from websocket buffer instantly. Event types: `door_open`, `door_close`, `access_granted`, `access_denied`, `door_alarm`
- **Historical events:** `access_list_events` with time/door/user filters. Topics: `admin` or `admin_activity`
- **Activity summary:** `access_get_activity_summary` aggregates events over a time period — useful for security audits
- **Credentials:** Create NFC (`{user_id, token}`), PIN (`{user_id, pin_code}`), or mobile (`{user_id}`) credentials
- **Visitor passes:** Time-bounded with ISO 8601 start/end times, optional email/phone for notifications

## Dual Authentication

Access has two independent auth paths:

- **API key (port 12445)** — for read-only operations (listing doors, events, devices)
- **Username + password (port 443)** — required for mutations (lock/unlock, credentials, visitors)

Either can work independently. For full functionality, configure both. If mutations fail with auth errors, the user needs username+password (API key alone is not enough for write operations).

To configure, run `/unifi-access:setup` or set env vars manually:
```
UNIFI_ACCESS_HOST=192.168.1.1
UNIFI_ACCESS_API_KEY=your-api-key
UNIFI_ACCESS_USERNAME=admin
UNIFI_ACCESS_PASSWORD=your-password
```

## Other UniFi Servers

If the user also has networking or cameras, other UniFi MCP plugins are available:
- `unifi-network` — network devices, clients, firewall, VPN, routing
- `unifi-protect` — security cameras, NVR, recordings, smart detections

Access readers are network clients — if a reader appears offline, the Network server can help check connectivity via `unifi_lookup_by_ip`.

## Tool Reference

For the complete list of all 29 tools organized by category with descriptions, tips, and common scenarios, read `references/access-tools.md`.
