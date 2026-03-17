# UniFi Protect MCP Server — Phase 2 Design Spec

**Date:** 2026-03-17
**Status:** Approved
**Scope:** Phase 2 — UniFi Protect MCP server with ~40 tools, real-time event streaming, camera snapshot resources
**Parent plan:** [unified-mcp-idea.md](../../plans/unified-mcp-idea.md)
**Depends on:** Phase 1 (monorepo, shared packages) — completed and released as `network/v0.7.0`

---

## Context

Phase 1 established the monorepo at `sirkirby/unifi-mcp` with shared packages (`unifi-core`, `unifi-mcp-shared`) and migrated the Network server. Phase 2 adds the second MCP server — UniFi Protect — covering cameras, smart detection, events, recordings, and NVR management.

This is the first server built on the shared infrastructure from scratch. It validates that the shared packages work as designed and establishes the pattern for future servers (Access in Phase 3).

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Library | `pyunifiprotect` (uiprotect) | Battle-tested (Home Assistant), async-first, deep private API coverage |
| Auth model | Dual auth, same as Network | Private API via pyunifiprotect (primary), API key for official endpoints where applicable |
| Connection manager | Thin wrapper (~100-150 lines) | pyunifiprotect manages its own lifecycle; we handle init/retry/cleanup |
| Event streaming | MCP resource subscriptions + websocket buffer | Standard MCP spec pattern; real-time push to agents |
| Media handling | URLs default, base64 optional, MCP image resources | Low token cost by default, multimodal support on request |
| Tool naming | `protect_` prefix | No `unifi_` prefix; MCP server namespacing handles disambiguation |
| Permissions | Read=true, mutations opt-in, delete denied | Same "secure by default" as Network |
| Deployment | Separate Docker image (`unifi-protect-mcp`) | Independent versioning and release cycle |
| Versioning | Prefixed tags (`protect/v0.1.0`) | Same pattern as Network |

---

## Repository Structure

```
apps/protect/
├── pyproject.toml                    # Package: unifi-protect-mcp
├── src/
│   └── unifi_protect_mcp/
│       ├── __init__.py
│       ├── main.py                   # FastMCP server, permissioned_tool, transport
│       ├── bootstrap.py              # Config loading, logging, Protect settings
│       ├── runtime.py                # Singleton factories (@lru_cache)
│       ├── tool_index.py             # Tool registry and discovery
│       ├── categories.py             # PROTECT_CATEGORY_MAP, TOOL_MODULE_MAP
│       ├── schemas.py                # JSON Schema input validation definitions
│       ├── validators.py             # Base validator class, response helpers
│       ├── validator_registry.py     # Validation dispatch
│       ├── config/
│       │   └── config.yaml           # Protect-specific config defaults
│       ├── managers/
│       │   ├── connection_manager.py # Thin wrapper around pyunifiprotect
│       │   ├── camera_manager.py     # Cameras, snapshots, PTZ, streams
│       │   ├── event_manager.py      # Events, smart detection, websocket buffer
│       │   ├── recording_manager.py  # Recording status, clip export
│       │   ├── light_manager.py      # Smart lights
│       │   ├── sensor_manager.py     # Door/window sensors
│       │   ├── chime_manager.py      # Chimes
│       │   ├── liveview_manager.py   # Liveviews and viewers
│       │   └── system_manager.py     # NVR info, health, firmware
│       ├── tools/
│       │   ├── cameras.py            # ~12 tools
│       │   ├── events.py             # ~10 tools
│       │   ├── recordings.py         # ~5 tools
│       │   ├── devices.py            # ~6 tools (lights, sensors, chimes)
│       │   ├── liveviews.py          # ~3 tools
│       │   └── system.py             # ~4 tools
│       ├── resources/
│       │   ├── snapshots.py          # MCP image resources for camera snapshots
│       │   └── events.py             # MCP subscribable resource for event stream
│       └── tools_manifest.json       # Pre-generated tool metadata
├── tests/
│   ├── conftest.py
│   └── unit/
├── devtools/
│   └── dev_console.py                # Interactive REPL for tool testing
├── scripts/
│   └── generate_tool_manifest.py
├── docs/
│   ├── configuration.md
│   ├── permissions.md
│   ├── tools.md
│   ├── events.md                     # Event streaming guide + client compatibility
│   └── troubleshooting.md
├── Dockerfile
├── Makefile                          # Full target set (test, lint, console, docker, etc.)
└── README.md
```

---

## Connection Manager

Thin wrapper around `pyunifiprotect`'s `ProtectApiClient`. ~100-150 lines.

**Responsibilities:**
- Initialize `ProtectApiClient` with credentials from config
- Integrate with `unifi-core` dual auth (pyunifiprotect handles local auth natively; API key path uses `unifi-core`)
- Lifecycle management: connect, disconnect, reconnect on failure via `unifi-core` retry
- WebSocket management: start/stop event subscription
- Expose `client` property for managers to call pyunifiprotect directly

**What it does NOT do (unlike Network's ConnectionManager):**
- No controller type detection (Protect is always UniFi OS)
- No path routing (pyunifiprotect handles API paths)
- No request-level caching (pyunifiprotect manages its own state)
- No CSRF/cookie management (pyunifiprotect handles auth internally)

**Managers access the underlying client:**
```python
class CameraManager:
    def __init__(self, connection_manager: ProtectConnectionManager):
        self._client = connection_manager.client

    async def list_cameras(self):
        return self._client.bootstrap.cameras
```

---

## Event Streaming Architecture

Real-time Protect events pushed to MCP clients via standard resource subscriptions.

### Flow

```
UniFi NVR                    Protect MCP Server              MCP Client
    |                              |                              |
    |-- WebSocket events --------->|                              |
    |   (motion, smart detect,     |                              |
    |    doorbell ring, etc.)      |                              |
    |                              |-- EventBuffer stores event   |
    |                              |                              |
    |                              |<-- resources/subscribe ------|
    |                              |    protect://events/stream   |
    |                              |                              |
    |                              |-- notification: ------------>|
    |                              |   resources/updated          |
    |                              |                              |
    |                              |<-- resources/read -----------|
    |                              |                              |
    |                              |-- Event data (JSON) -------->|
```

### Components

**EventBuffer** (in `event_manager.py`):
- Ring buffer of recent events from NVR websocket
- Configurable: buffer size (default 100), TTL (default 300 seconds)
- Filterable by event type, camera ID, confidence score
- Shared between the MCP resource and the `protect_recent_events` polling tool

**Event Stream Resource** (`resources/events.py`):
- MCP resource at `protect://events/stream`
- Clients subscribe via `resources/subscribe`
- Server sends `notifications/resources/updated` when new events arrive
- Resource read returns latest events as JSON array

**Configuration:**
```yaml
protect:
  events:
    buffer_size: 100
    buffer_ttl_seconds: 300
    websocket_enabled: true
    smart_detection_min_confidence: 50
```

**Graceful degradation:**
- WebSocket disconnects → reconnect with `unifi-core` retry
- Client doesn't support subscriptions → use `protect_recent_events` polling tool
- WebSocket disabled in config → event tools fall back to REST API calls

### Client Compatibility

Document which MCP clients support resource subscriptions. Research during implementation and include in `docs/events.md`.

---

## MCP Resources

### Camera Snapshots

```
protect://cameras/{camera_id}/snapshot
```

- Returns `image/jpeg` content
- Fetches live snapshot on each read
- Dynamically registered after NVR connection (one per discovered camera)
- Use case: multimodal LLMs viewing camera feeds

### Event Stream

```
protect://events/stream
```

- Returns JSON array of recent events from websocket buffer
- Subscribable with `notifications/resources/updated` push
- Use case: agents monitoring for events

---

## Tool Catalog (~40 tools)

### Cameras (~12 tools)

| Tool | Action | Auth | Description |
|------|--------|------|-------------|
| `protect_list_cameras` | read | either | List all cameras with status |
| `protect_get_camera` | read | either | Camera details by ID |
| `protect_get_snapshot` | read | either | Current snapshot (URL or base64 via `include_image`) |
| `protect_get_camera_streams` | read | either | RTSP/RTSPS stream URLs |
| `protect_update_camera_settings` | update | local_only | IR mode, HDR, mic, status light |
| `protect_toggle_recording` | update | local_only | Enable/disable recording |
| `protect_ptz_move` | update | local_only | Pan/tilt/zoom control |
| `protect_ptz_preset` | update | local_only | Go to PTZ preset position |
| `protect_reboot_camera` | update | local_only | Reboot camera |
| `protect_get_camera_analytics` | read | either | Motion heatmap, activity stats |

### Events & Smart Detection (~10 tools)

| Tool | Action | Auth | Description |
|------|--------|------|-------------|
| `protect_list_events` | read | either | Events with time range/type/camera filters |
| `protect_get_event` | read | either | Single event details |
| `protect_get_event_thumbnail` | read | either | Event thumbnail (URL or base64) |
| `protect_list_smart_detections` | read | either | Person/vehicle/animal/package with confidence |
| `protect_recent_events` | read | either | From websocket buffer (fast, no API call) |
| `protect_subscribe_events` | read | either | Start subscription (returns resource URI) |
| `protect_acknowledge_event` | update | local_only | Mark event as acknowledged |

### Recordings (~5 tools)

| Tool | Action | Auth | Description |
|------|--------|------|-------------|
| `protect_list_recordings` | read | either | Recording segments for a camera |
| `protect_get_recording_status` | read | either | Current recording state per camera |
| `protect_export_clip` | read | either | Export video clip (download URL) |
| `protect_generate_timelapse` | read | either | Generate timelapse (URL) |
| `protect_delete_recording` | delete | local_only | Delete recording segment |

### Devices — Lights, Sensors, Chimes (~6 tools)

| Tool | Action | Auth | Description |
|------|--------|------|-------------|
| `protect_list_lights` | read | either | All smart lights |
| `protect_update_light` | update | local_only | Brightness, auto-on settings |
| `protect_list_sensors` | read | either | All door/window sensors |
| `protect_list_chimes` | read | either | All chimes |
| `protect_update_chime` | update | local_only | Volume, ringtone |
| `protect_trigger_chime` | update | local_only | Play chime sound |

### Liveviews (~3 tools)

| Tool | Action | Auth | Description |
|------|--------|------|-------------|
| `protect_list_liveviews` | read | either | All configured liveviews |
| `protect_create_liveview` | create | local_only | Create new liveview layout |
| `protect_delete_liveview` | delete | local_only | Delete liveview |

### System (~4 tools)

| Tool | Action | Auth | Description |
|------|--------|------|-------------|
| `protect_get_system_info` | read | either | NVR info, version, storage |
| `protect_get_health` | read | either | System health check |
| `protect_list_viewers` | read | either | Connected viewers |
| `protect_get_firmware_status` | read | either | Firmware update availability |

---

## Permission Defaults

```yaml
permissions:
  default:
    read: true
    create: false
    update: false
    delete: false
  cameras:
    read: true
    update: false
  events:
    read: true
    update: false
  recordings:
    read: true
    delete: false
  lights:
    read: true
    update: false
  sensors:
    read: true
  chimes:
    read: true
    update: false
  liveviews:
    read: true
    create: false
    delete: false
  system:
    read: true
    update: false
```

Same env var override pattern: `UNIFI_PERMISSIONS_CAMERAS_UPDATE=true`.

---

## Build & Deployment

### pyproject.toml

```
name = "unifi-protect-mcp"
dependencies: unifi-core, unifi-mcp-shared, mcp[cli], pyunifiprotect, aiohttp, pyyaml, python-dotenv, omegaconf
version: hatch-vcs with tag_regex matching protect/v*
entry point: unifi-protect-mcp = "unifi_protect_mcp.main:main"
```

### CI Workflows

| Workflow | Triggers | Purpose |
|----------|----------|---------|
| `test-protect.yml` | push to main, PRs | Run Protect tests |
| `docker-protect.yml` | push to main, `protect/v*` tags | Build `ghcr.io/sirkirby/unifi-protect-mcp` |
| `publish-protect.yml` | GitHub release with `protect/v*` tag | Publish to PyPI |

### Docker

- Separate image: `ghcr.io/sirkirby/unifi-protect-mcp`
- Same Dockerfile pattern as Network (uv sync --frozen, venv PATH)
- Port 3001 (Network uses 3000)
- Added to `docker/docker-compose.yml` as second service

### docker-compose.yml update

```yaml
services:
  unifi-network-mcp:
    # ... existing network service on port 3000

  unifi-protect-mcp:
    build:
      context: ..
      dockerfile: apps/protect/Dockerfile
    env_file:
      - ../.env
    environment:
      - UNIFI_MCP_HTTP_ENABLED=true
      - UNIFI_MCP_HTTP_TRANSPORT=streamable-http
      - UNIFI_MCP_HOST=0.0.0.0
      - UNIFI_MCP_PORT=3001
      - UNIFI_MCP_ALLOWED_HOSTS=localhost,localhost:3001,127.0.0.1,127.0.0.1:3001,host.docker.internal,host.docker.internal:3001
    ports:
      - "3001:3001"
    restart: unless-stopped
    container_name: unifi-protect-mcp
```

### Makefile

Full target set matching Network: test, test-cov, lint, format, manifest, run (all modes), console (all variants), docker, docker-run, build, build-check, pre-commit, pre-release, deps-check, deps-update, info, permission testing helpers.

### Dev Console

`apps/protect/devtools/dev_console.py` — interactive REPL for testing Protect tools against a live NVR. Same pattern as Network's dev console with Protect-specific commands.

---

## Root Makefile Updates

```makefile
protect-test:
    $(MAKE) -C apps/protect test

protect-lint:
    $(MAKE) -C apps/protect lint

protect-format:
    $(MAKE) -C apps/protect format

protect-manifest:
    $(MAKE) -C apps/protect manifest

test: core-test shared-test network-test protect-test
lint: network-lint protect-lint
format: network-format protect-format
```

---

## PR Sequencing

Each PR leaves tests green. No release until all 8 PRs land.

| PR | Scope | Risk |
|----|-------|------|
| **1** | App scaffold: directory structure, pyproject.toml, Makefile, Dockerfile, config.yaml, categories.py, empty modules | Low |
| **2** | Connection manager + system tools (prove pyunifiprotect integration end to end) | Medium |
| **3** | Camera tools (list, get, snapshot, streams, settings, PTZ, reboot) | Medium |
| **4** | Event tools + websocket buffer + MCP resource subscription | **High** — novel streaming architecture |
| **5** | Recording tools + device tools (lights, sensors, chimes) + liveview tools | Low-medium |
| **6** | MCP snapshot resources + image handling (base64 support) | Medium |
| **7** | CI workflows, Docker, docker-compose, dev console | Low |
| **8** | Documentation, README, permissions guide, tools catalog, event streaming guide | Low |

After PR 8: tag `protect/v0.1.0`, publish to PyPI, push Docker image, update root README status table.

---

## What's NOT in Phase 2

- **Private API deep tools** — requires additional research; Phase 2+ follow-up
- **Cross-server orchestration** — Agent SDK integration (Phase 3+)
- **Video analytics ML** — out of scope (Protect NVR handles this)
- **Multi-NVR support** — single NVR per server instance for now
- **Access server** — Phase 3, separate design cycle
