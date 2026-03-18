---
name: unifi-protect
description: How to manage UniFi Protect cameras and NVR — view cameras, smart detections, recordings, snapshots, lights, and sensors. Use this skill when the user mentions UniFi cameras, security cameras, NVR, recordings, motion detection, person detection, snapshots, RTSP streams, floodlights, sensors, chimes, or any UniFi Protect task.
---

# UniFi Protect MCP Server

You have access to a UniFi Protect MCP server that lets you query and manage a UniFi Protect NVR. It provides 34 tools covering cameras, smart detections, recordings, snapshots, lights, sensors, and chimes.

## Tool Discovery

The server uses **lazy loading** by default — only meta-tools are registered initially:

| Meta-Tool | Purpose |
|-----------|---------|
| `protect_tool_index` | List all 34 tools with full parameter schemas |
| `protect_execute` | Call any tool by name (essential in lazy mode) |
| `protect_batch` | Run multiple tools in parallel |
| `protect_batch_status` | Check async batch job status |

**Workflow:** Call `protect_tool_index` to find the right tool, then `protect_execute` to call it. Use `protect_batch` for multiple independent queries.

## Safety Model

**All mutations are disabled by default** because Protect controls physical security hardware.

**Read operations** — always available. Listing cameras, events, snapshots, sensor readings — all work without permissions.

**Mutations** require explicit opt-in via env vars:
- `UNIFI_PERMISSIONS_CAMERAS_UPDATE=true` — camera settings, recording toggle, PTZ, reboot
- `UNIFI_PERMISSIONS_LIGHTS_UPDATE=true` — light brightness, PIR sensitivity
- `UNIFI_PERMISSIONS_CHIMES_UPDATE=true` — chime volume, trigger

**Confirmation flow** — every mutation uses preview-then-confirm:
1. Default call → returns preview of what would change
2. Call with `confirm=true` → executes the mutation

Always preview first and show the user before confirming.

## Response Format

All tools return: `{"success": true, "data": ...}`, `{"success": false, "error": "..."}`, or `{"success": true, "requires_confirmation": true, "preview": ...}`. Always check `success` first.

## Key Capabilities

- **Snapshots:** `protect_get_snapshot` with `include_image=true` returns base64 JPEG inline
- **RTSP streams:** `protect_get_camera_streams` gives stream URLs for video player integration
- **Smart detections:** `protect_list_smart_detections` filters by type (person, vehicle, animal, package, face, licensePlate)
- **Real-time events:** `protect_recent_events` reads from websocket buffer instantly (no API call). Use `protect_list_events` for historical queries
- **Video export:** `protect_export_clip` returns metadata (not video data — too large for MCP). Max 2 hours, supports timelapse (fps: 4=60x, 8=120x, 20=300x)
- **PTZ:** Only zoom works via API. For pan/tilt, use `protect_ptz_preset` with saved positions

## Authentication

Username and password are **required** (local admin credentials, not Ubiquiti SSO). API key support exists but is **experimental** — limited to read-only operations and a subset of tools.

To configure, run `/unifi-protect:setup` or set env vars manually:
```
UNIFI_PROTECT_HOST=192.168.1.1
UNIFI_PROTECT_USERNAME=admin
UNIFI_PROTECT_PASSWORD=your-password
```

## Other UniFi Servers

If the user also has networking or door access control, other UniFi MCP plugins are available:
- `unifi-network` — network devices, clients, firewall, VPN, routing
- `unifi-access` — door locks, credentials, visitors, access policies

Cameras are network clients — if a camera appears offline, the Network server can help check connectivity via `unifi_lookup_by_ip`.

## Tool Reference

For the complete list of all 34 tools organized by category with descriptions, tips, and common scenarios, read `references/protect-tools.md`.
