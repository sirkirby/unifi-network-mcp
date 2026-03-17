# UniFi Protect MCP Server — Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new UniFi Protect MCP server with ~40 tools, real-time event streaming via MCP resource subscriptions, and camera snapshot resources.

**Architecture:** New server at `apps/protect/` in the monorepo, following Network app patterns. Uses `pyunifiprotect` for NVR communication, `unifi-core` for auth/retry, and `unifi-mcp-shared` for permissions/lazy-loading/meta-tools. Novel features: websocket event buffer with MCP resource subscription push, camera snapshot MCP resources.

**Tech Stack:** Python 3.13+, FastMCP, pyunifiprotect, aiohttp, OmegaConf, uv workspaces, hatch-vcs, ruff, pytest

**Spec:** `docs/superpowers/specs/2026-03-17-unifi-protect-mcp-design.md`

**Reference:** `apps/network/` (follow its patterns for structure, imports, tool definitions, Makefile, Dockerfile, pyproject.toml)

---

## Chunk 1: PR 1 — App Scaffold

### Task 1: Create directory structure and package files

**Files:**
- Create: `apps/protect/` (full directory tree)
- Create: `apps/protect/pyproject.toml`
- Create: `apps/protect/src/unifi_protect_mcp/__init__.py`
- Create: `apps/protect/Makefile`
- Create: `apps/protect/Dockerfile`
- Create: `apps/protect/README.md` (placeholder)

- [ ] **Step 1: Create directory scaffold**

```bash
mkdir -p apps/protect/src/unifi_protect_mcp/{config,managers,tools,resources,utils}
mkdir -p apps/protect/{tests/unit,devtools,scripts,docs}
```

- [ ] **Step 2: Create `apps/protect/pyproject.toml`**

Adapt from `apps/network/pyproject.toml`. Key differences:
- `name = "unifi-protect-mcp"`
- Entry point: `unifi-protect-mcp = "unifi_protect_mcp.main:main"`
- Dependencies: replace `aiounifi>=88` with `pyunifiprotect>=5.0.0` (or `uiprotect`)
- `tag_regex` matches `protect/v*` (not `network/v*`)
- `known-first-party = ["unifi_protect_mcp"]`
- Workspace sources: `unifi-mcp-shared` and `unifi-core`

- [ ] **Step 3: Create `apps/protect/src/unifi_protect_mcp/__init__.py`**

```python
"""UniFi Protect MCP Server."""
```

- [ ] **Step 4: Create `apps/protect/Makefile`**

Copy from `apps/network/Makefile`, replacing all `network` references with `protect` and `unifi-network-mcp` with `unifi-protect-mcp`. Full target set: test, lint, format, manifest, run modes, console variants, docker, build, pre-release, deps, info, permission testing.

- [ ] **Step 5: Create `apps/protect/Dockerfile`**

Same pattern as Network's Dockerfile. Replace `unifi-network-mcp` with `unifi-protect-mcp`. Port remains 3000 internally (compose maps to 3001 externally).

- [ ] **Step 6: Create placeholder `README.md`**

Brief placeholder — full README in PR 8.

- [ ] **Step 7: Commit**

```bash
git add apps/protect/
git commit -m "chore: scaffold Protect MCP server app structure"
```

### Task 2: Create config and bootstrap

**Files:**
- Create: `apps/protect/src/unifi_protect_mcp/config/config.yaml`
- Create: `apps/protect/src/unifi_protect_mcp/bootstrap.py`

- [ ] **Step 1: Create `config/config.yaml`**

Adapt from Network's config.yaml. Key differences:
- Same `unifi:` section (host, username, password, port, site, verify_ssl, api_key)
- `server:` section same structure (host, port, log_level, tool_registration_mode, http config)
- `protect:` section for event buffer config:
  ```yaml
  protect:
    events:
      buffer_size: 100
      buffer_ttl_seconds: 300
      websocket_enabled: true
      smart_detection_min_confidence: 50
  ```
- `permissions:` section with Protect-specific categories (cameras, events, recordings, lights, sensors, chimes, liveviews, system). All mutations default false.

- [ ] **Step 2: Create `bootstrap.py`**

Adapt from Network's bootstrap.py. Key differences:
- `ProtectSettings` dataclass instead of `UniFiSettings` (same fields — host, username, password, port, site, verify_ssl, api_key)
- Logger name: `"unifi-protect-mcp"`
- Same `load_config()` pattern using `unifi_mcp_shared.config` helpers
- Same env var override loop for `UNIFI_*` variables
- No controller_type config (Protect is always UniFi OS)

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(protect): add config and bootstrap modules"
```

### Task 3: Create categories, tool_index, runtime, and main stubs

**Files:**
- Create: `apps/protect/src/unifi_protect_mcp/categories.py`
- Create: `apps/protect/src/unifi_protect_mcp/tool_index.py`
- Create: `apps/protect/src/unifi_protect_mcp/runtime.py`
- Create: `apps/protect/src/unifi_protect_mcp/main.py`

- [ ] **Step 1: Create `categories.py`**

```python
"""Protect server permission category mappings and tool module map."""

PROTECT_CATEGORY_MAP = {
    "camera": "cameras",
    "event": "events",
    "recording": "recordings",
    "light": "lights",
    "sensor": "sensors",
    "chime": "chimes",
    "liveview": "liveviews",
    "system": "system",
}

# TOOL_MODULE_MAP built from manifest at import time
from unifi_mcp_shared.lazy_tools import build_tool_module_map
import importlib.resources

_manifest_ref = importlib.resources.files("unifi_protect_mcp").joinpath("tools_manifest.json")
_manifest_path = str(_manifest_ref) if _manifest_ref.is_file() else None

TOOL_MODULE_MAP = build_tool_module_map(
    tools_package="unifi_protect_mcp.tools",
    manifest_path=_manifest_path,
)
```

- [ ] **Step 2: Create `tool_index.py`**

Copy from Network's `tool_index.py`, replacing `unifi_network_mcp` references with `unifi_protect_mcp`. Same `ToolMetadata` dataclass, `register_tool()`, `get_tool_index()`.

- [ ] **Step 3: Create `runtime.py`**

Adapt from Network's runtime.py. Key differences:
- Import `ProtectConnectionManager` instead of `ConnectionManager`
- Manager factories for: camera, event, recording, light, sensor, chime, liveview, system managers
- `get_auth()` factory from `unifi-core`
- Same `@lru_cache` + alias pattern

Initially, manager factories will reference classes that don't exist yet — that's fine, they'll be stubbed.

- [ ] **Step 4: Create `main.py`**

Adapt from Network's main.py. Key differences:
- Import from `unifi_protect_mcp.*` instead of `unifi_network_mcp.*`
- Use `PROTECT_CATEGORY_MAP` for PermissionChecker
- Server name: `"unifi-protect-mcp"`
- Same `permissioned_tool` decorator pattern
- Same registration modes (lazy/eager/meta_only)
- Same transport dispatch (stdio + optional HTTP)

- [ ] **Step 5: Create empty manager stubs**

Create empty files with docstrings for all managers in `managers/`:
- `connection_manager.py`
- `camera_manager.py`, `event_manager.py`, `recording_manager.py`
- `light_manager.py`, `sensor_manager.py`, `chime_manager.py`
- `liveview_manager.py`, `system_manager.py`

Each with a class stub:
```python
"""Camera management for UniFi Protect."""

class CameraManager:
    def __init__(self, connection_manager):
        self._cm = connection_manager
```

- [ ] **Step 6: Create empty tool module stubs**

Create empty files for all tool modules in `tools/`:
- `cameras.py`, `events.py`, `recordings.py`, `devices.py`, `liveviews.py`, `system.py`

- [ ] **Step 7: Create empty resource stubs**

- `resources/__init__.py`
- `resources/snapshots.py`
- `resources/events.py`

- [ ] **Step 8: Create schemas, validators, validator_registry stubs**

Copy structure from Network but with empty/minimal content.

- [ ] **Step 9: Create conftest.py**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

- [ ] **Step 10: Create generate_tool_manifest.py**

Adapt from Network's script, replacing paths and package names.

- [ ] **Step 11: Update root workspace**

Verify `uv sync` picks up the new package. The root `pyproject.toml` workspace members `apps/*` should auto-discover it.

```bash
uv sync
```

- [ ] **Step 12: Update root Makefile**

Add `protect-test`, `protect-lint`, `protect-format`, `protect-manifest` targets. Update aggregate `test`, `lint`, `format` to include Protect.

- [ ] **Step 13: Run tests and verify**

```bash
make protect-test  # Should pass (no tests yet, or empty)
make protect-lint   # Should pass
```

- [ ] **Step 14: Commit**

```bash
git commit -m "feat(protect): add categories, runtime, main, and module stubs"
```

### Task 4: Verify PR 1

- [ ] **Step 1: Full workspace test**

```bash
make test
```
Expected: All existing tests pass, Protect has no failures.

- [ ] **Step 2: Verify package installs**

```bash
uv run --package unifi-protect-mcp python -c "import unifi_protect_mcp; print('OK')"
```

---

## Chunk 2: PR 2 — Connection Manager + System Tools

### Task 5: Implement ProtectConnectionManager

**Files:**
- Create: `apps/protect/src/unifi_protect_mcp/managers/connection_manager.py`
- Create: `apps/protect/tests/unit/test_connection_manager.py`

- [ ] **Step 1: Write test for initialization**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_connection_manager_init():
    """Connection manager stores config and starts uninitialized."""
    from unifi_protect_mcp.managers.connection_manager import ProtectConnectionManager
    cm = ProtectConnectionManager(
        host="192.168.1.1", username="admin", password="test",
        port=443, site="default", verify_ssl=False,
    )
    assert cm.host == "192.168.1.1"
    assert cm._initialized is False
    assert cm.client is None
```

- [ ] **Step 2: Implement ProtectConnectionManager**

~100-150 lines. Key features:
- Constructor stores config, sets `_initialized = False`
- `async initialize()`: creates `ProtectApiClient`, calls `client.update()`, marks initialized
- `client` property: returns the pyunifiprotect client (or raises if not initialized)
- `api_session` property: returns aiohttp session with API key header (via unifi-core)
- `async start_websocket()`: starts event subscription
- `async close()`: clean shutdown
- Retry via `unifi-core`'s `retry_with_backoff` for initial connection only
- pyunifiprotect handles its own websocket reconnection

Reference: Network's `connection_manager.py` for the pattern, but MUCH simpler (no detection, no CSRF, no caching).

- [ ] **Step 3: Write additional tests**

Test error handling, retry behavior (mock pyunifiprotect), websocket start/stop.

- [ ] **Step 4: Update runtime.py**

Wire `get_connection_manager()` factory to use real `ProtectConnectionManager`.

- [ ] **Step 5: Run tests, commit**

```bash
make protect-test
git commit -m "feat(protect): implement ProtectConnectionManager"
```

### Task 6: Implement SystemManager + system tools

**Files:**
- Implement: `apps/protect/src/unifi_protect_mcp/managers/system_manager.py`
- Create: `apps/protect/src/unifi_protect_mcp/tools/system.py`
- Create: `apps/protect/tests/unit/test_system.py`

- [ ] **Step 1: Implement SystemManager**

Methods:
- `get_system_info()` — NVR model, version, uptime, storage
- `get_health()` — system health summary
- `list_viewers()` — connected viewers
- `get_firmware_status()` — firmware update availability

Each method accesses `self._cm.client.bootstrap` (pyunifiprotect's cached NVR state).

- [ ] **Step 2: Implement system tools**

4 tools following the Network thin-wrapper pattern:
- `protect_get_system_info`
- `protect_get_health`
- `protect_list_viewers`
- `protect_get_firmware_status`

Each tool: `@server.tool()` with name, description, ToolAnnotations (readOnlyHint=True), delegates to manager, returns `{"success": True, "data": ...}`.

- [ ] **Step 3: Write tests**

Test each tool with mocked connection manager. Verify response format.

- [ ] **Step 4: Add tools to TOOL_MODULE_MAP in categories.py**

- [ ] **Step 5: Generate manifest**

```bash
make protect-manifest
```

- [ ] **Step 6: Run tests, commit**

```bash
make protect-test
git commit -m "feat(protect): add system manager and 4 system tools"
```

### Task 7: End-to-end verification (PR 2)

- [ ] **Step 1: Verify dev console starts**

Create minimal `devtools/dev_console.py` that imports and initializes the server.

- [ ] **Step 2: Full test suite**

```bash
make test
```

- [ ] **Step 3: Lint and format**

```bash
make protect-lint && make protect-format
```

---

## Chunk 3: PR 3 — Camera Tools

### Task 8: Implement CameraManager

**Files:**
- Implement: `apps/protect/src/unifi_protect_mcp/managers/camera_manager.py`
- Create: `apps/protect/tests/unit/test_camera_manager.py`

- [ ] **Step 1: Implement CameraManager**

Methods:
- `list_cameras()` — all cameras from `client.bootstrap.cameras`
- `get_camera(camera_id)` — single camera details
- `get_snapshot(camera_id, width, height)` — fetch snapshot bytes from camera
- `get_camera_streams(camera_id)` — RTSP/RTSPS URLs
- `update_camera_settings(camera_id, settings)` — update IR, HDR, mic, etc.
- `toggle_recording(camera_id, enabled)` — enable/disable recording
- `ptz_move(camera_id, pan, tilt, zoom)` — PTZ control
- `ptz_preset(camera_id, preset_id)` — go to preset
- `reboot_camera(camera_id)` — reboot
- `get_camera_analytics(camera_id)` — motion stats (implementation-dependent)

- [ ] **Step 2: Write tests for CameraManager**

Mock `ProtectApiClient` and its `bootstrap.cameras` dict. Test list, get, error handling.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat(protect): implement CameraManager with 10 methods"
```

### Task 9: Implement camera tools

**Files:**
- Implement: `apps/protect/src/unifi_protect_mcp/tools/cameras.py`
- Create: `apps/protect/tests/unit/test_camera_tools.py`

- [ ] **Step 1: Implement ~10-12 camera tools**

Follow the thin-wrapper pattern from Network. Each tool:
1. `@server.tool(name="protect_...", description="...", annotations=ToolAnnotations(...))`
2. Validate input
3. Call manager method
4. Format and return response

For `protect_get_snapshot`: support `include_image: bool = False` parameter. When True, return base64-encoded image. When False (default), return snapshot URL.

Mutation tools (`update_camera_settings`, `toggle_recording`, `ptz_move`, `ptz_preset`, `reboot_camera`): implement preview-then-confirm pattern via `unifi_mcp_shared.confirmation`.

- [ ] **Step 2: Write tests**

Test each tool with mocked camera manager. Verify:
- Read tools return `{"success": True, "data": ...}`
- Mutation tools return preview when `confirm=False`
- Error cases return `{"success": False, "error": "..."}`

- [ ] **Step 3: Update TOOL_MODULE_MAP, regenerate manifest**

- [ ] **Step 4: Run tests, commit**

```bash
make protect-test
git commit -m "feat(protect): add 10 camera tools"
```

### Task 10: Verify PR 3

- [ ] **Step 1: Full test suite**
- [ ] **Step 2: Lint and format**
- [ ] **Step 3: Verify manifest is up to date**

---

## Chunk 4: PR 4 — Events + Streaming (Highest Risk)

### Task 11: Implement EventBuffer

**Files:**
- Implement: `apps/protect/src/unifi_protect_mcp/managers/event_manager.py` (EventBuffer class)
- Create: `apps/protect/tests/unit/test_event_buffer.py`

- [ ] **Step 1: Write EventBuffer tests**

```python
import pytest
from unifi_protect_mcp.managers.event_manager import EventBuffer

def test_buffer_stores_events():
    buf = EventBuffer(max_size=5, ttl_seconds=300)
    buf.add({"type": "motion", "camera": "cam1", "timestamp": 1234})
    assert len(buf.get_recent()) == 1

def test_buffer_respects_max_size():
    buf = EventBuffer(max_size=3, ttl_seconds=300)
    for i in range(5):
        buf.add({"type": "motion", "id": i})
    assert len(buf.get_recent()) == 3

def test_buffer_filters_by_type():
    buf = EventBuffer(max_size=10, ttl_seconds=300)
    buf.add({"type": "motion", "camera": "cam1"})
    buf.add({"type": "smartDetect", "camera": "cam1"})
    results = buf.get_recent(event_type="smartDetect")
    assert len(results) == 1

def test_buffer_filters_by_camera():
    buf = EventBuffer(max_size=10, ttl_seconds=300)
    buf.add({"type": "motion", "camera_id": "cam1"})
    buf.add({"type": "motion", "camera_id": "cam2"})
    results = buf.get_recent(camera_id="cam1")
    assert len(results) == 1
```

- [ ] **Step 2: Implement EventBuffer**

Ring buffer backed by `collections.deque(maxlen=N)`. Methods:
- `add(event)` — add event with timestamp, trim expired
- `get_recent(event_type=None, camera_id=None, min_confidence=None, limit=None)` — filtered query
- `clear()` — reset buffer
- TTL enforcement on read (lazy expiration)

- [ ] **Step 3: Run tests, commit**

```bash
git commit -m "feat(protect): implement EventBuffer ring buffer"
```

### Task 12: Implement EventManager with websocket integration

**Files:**
- Implement: `apps/protect/src/unifi_protect_mcp/managers/event_manager.py` (EventManager class)
- Create: `apps/protect/tests/unit/test_event_manager.py`

- [ ] **Step 1: Implement EventManager**

- Constructor takes `ProtectConnectionManager` + event config
- `start_listening()` — register callback on pyunifiprotect's websocket
- `_on_event(event)` — callback: parse event, add to EventBuffer, trigger MCP notification
- `list_events(start, end, event_type, camera_id)` — REST API query via pyunifiprotect
- `get_event(event_id)` — single event details
- `get_event_thumbnail(event_id)` — thumbnail bytes
- `list_smart_detections(start, end, camera_id, min_confidence)` — filtered smart detections
- `get_recent_from_buffer(...)` — delegates to EventBuffer
- `acknowledge_event(event_id)` — mark as acknowledged

- [ ] **Step 2: Write tests with mocked pyunifiprotect**
- [ ] **Step 3: Commit**

### Task 13: Implement event stream MCP resource

**Files:**
- Implement: `apps/protect/src/unifi_protect_mcp/resources/events.py`
- Create: `apps/protect/tests/unit/test_event_resource.py`

- [ ] **Step 1: Research FastMCP resource subscription API**

Before implementing, verify:
- How to register a subscribable resource with `@server.resource()`
- How to send `ResourceUpdatedNotification` from a background callback
- Minimum `mcp[cli]` version needed for resource subscriptions
- Whether `server.request_context` or `ctx.send_notification()` is needed

Read FastMCP docs or source for the exact API.

- [ ] **Step 2: Implement event stream resource**

```python
# resources/events.py
from mcp.types import ResourceUpdatedNotification

@server.resource("protect://events/stream")
async def event_stream_resource() -> str:
    """Real-time event stream from UniFi Protect NVR."""
    events = event_manager.get_recent_from_buffer()
    return json.dumps(events)
```

The websocket callback in EventManager triggers the notification:
```python
async def _on_event(self, event):
    self._buffer.add(event)
    # Notify subscribed MCP clients
    await self._server.send_notification(
        ResourceUpdatedNotification(uri="protect://events/stream")
    )
```

- [ ] **Step 3: Write tests**

Test that:
- Resource read returns buffered events as JSON
- New event triggers notification (mock server.send_notification)
- Empty buffer returns empty array

- [ ] **Step 4: Commit**

```bash
git commit -m "feat(protect): implement event stream MCP resource with subscriptions"
```

### Task 14: Implement event tools

**Files:**
- Implement: `apps/protect/src/unifi_protect_mcp/tools/events.py`
- Create: `apps/protect/tests/unit/test_event_tools.py`

- [ ] **Step 1: Implement ~7 event tools**

- `protect_list_events` — time range + filters, REST API
- `protect_get_event` — single event by ID
- `protect_get_event_thumbnail` — thumbnail URL or base64
- `protect_list_smart_detections` — filtered by type, confidence
- `protect_recent_events` — from buffer (fast, no API call)
- `protect_subscribe_events` — returns resource URI + instructions
- `protect_acknowledge_event` — mutation with confirm pattern

- [ ] **Step 2: Write tests**
- [ ] **Step 3: Update TOOL_MODULE_MAP, regenerate manifest**
- [ ] **Step 4: Run full test suite, commit**

```bash
git commit -m "feat(protect): add 7 event tools with streaming support"
```

### Task 15: Wire websocket into main.py startup

- [ ] **Step 1: Update main_async()**

After connection initialization, start the websocket listener:
```python
if config.protect.events.websocket_enabled:
    await event_manager.start_listening()
```

- [ ] **Step 2: Verify event streaming end-to-end**

This requires a live NVR. Document manual test procedure in PR description.

- [ ] **Step 3: Commit**

---

## Chunk 5: PR 5 — Recordings, Devices, Liveviews

### Task 16: Implement RecordingManager + recording tools

**Files:**
- Implement: `managers/recording_manager.py`, `tools/recordings.py`
- Create: `tests/unit/test_recordings.py`

5 tools: `protect_list_recordings`, `protect_get_recording_status`, `protect_export_clip`, `protect_generate_timelapse`, `protect_delete_recording`.

Note: `protect_export_clip` may need `create` permission action (triggers NVR-side processing). `protect_generate_timelapse` is implementation-dependent — skip if pyunifiprotect doesn't support it and add to backlog.

- [ ] **Step 1: Implement manager methods**
- [ ] **Step 2: Implement 4-5 recording tools**
- [ ] **Step 3: Write tests, commit**

### Task 17: Implement device managers + device tools

**Files:**
- Implement: `managers/light_manager.py`, `managers/sensor_manager.py`, `managers/chime_manager.py`
- Implement: `tools/devices.py`
- Create: `tests/unit/test_devices.py`

6 tools: `protect_list_lights`, `protect_update_light`, `protect_list_sensors`, `protect_list_chimes`, `protect_update_chime`, `protect_trigger_chime`.

Each manager is small (~50-80 lines). One tool module for all three device types since they're simple CRUD.

- [ ] **Step 1: Implement 3 device managers**
- [ ] **Step 2: Implement 6 device tools**
- [ ] **Step 3: Write tests, commit**

### Task 18: Implement LiveviewManager + liveview tools

**Files:**
- Implement: `managers/liveview_manager.py`, `tools/liveviews.py`
- Create: `tests/unit/test_liveviews.py`

3 tools: `protect_list_liveviews`, `protect_create_liveview`, `protect_delete_liveview`.

- [ ] **Step 1: Implement manager + tools + tests**
- [ ] **Step 2: Commit**

### Task 19: Verify PR 5

- [ ] **Step 1: Update TOOL_MODULE_MAP for all new tools**
- [ ] **Step 2: Regenerate manifest**
- [ ] **Step 3: Full test suite, lint, format**

---

## Chunk 6: PR 6 — Snapshot Resources + Image Handling

### Task 20: Implement camera snapshot MCP resources

**Files:**
- Implement: `apps/protect/src/unifi_protect_mcp/resources/snapshots.py`
- Create: `apps/protect/tests/unit/test_snapshot_resource.py`

- [ ] **Step 1: Research FastMCP dynamic resource registration**

Camera snapshot resources are registered dynamically after NVR connection (one per camera). Research:
- `server.add_resource()` for dynamic registration
- Resource templates (`protect://cameras/{camera_id}/snapshot`) if supported
- Binary content (image/jpeg) in resource responses

- [ ] **Step 2: Implement snapshot resource registration**

After `connection_manager.initialize()`, enumerate cameras and register a resource for each:

```python
for camera in connection_manager.client.bootstrap.cameras.values():
    @server.resource(f"protect://cameras/{camera.id}/snapshot", mime_type="image/jpeg")
    async def camera_snapshot(cam_id=camera.id):
        return await camera_manager.get_snapshot(cam_id)
```

Or use a resource template if FastMCP supports parameterized URIs.

- [ ] **Step 3: Add base64 support to protect_get_snapshot tool**

Ensure the `include_image=True` parameter on `protect_get_snapshot` returns base64-encoded JPEG in the response data.

- [ ] **Step 4: Write tests, commit**

```bash
git commit -m "feat(protect): add camera snapshot MCP resources and base64 image support"
```

---

## Chunk 7: PR 7 — CI, Docker, Dev Console

### Task 21: Create CI workflows

**Files:**
- Create: `.github/workflows/test-protect.yml`
- Create: `.github/workflows/docker-protect.yml`
- Create: `.github/workflows/publish-protect.yml`

- [ ] **Step 1: Create `test-protect.yml`**

Adapt from `test-network.yml`. Run on push to main + PRs. Key differences:
- pytest path: `apps/protect/tests`
- Package: `--package unifi-protect-mcp`
- Coverage target: `unifi_protect_mcp`

- [ ] **Step 2: Create `docker-protect.yml`**

Adapt from `docker-network.yml`. Key differences:
- Image name: `${{ github.repository_owner }}/unifi-protect-mcp`
- Dockerfile: `apps/protect/Dockerfile`
- Tag triggers: `protect/v*.*.*`
- Version detection: match `protect/v*` tags

- [ ] **Step 3: Create `publish-protect.yml`**

Adapt from `publish-network.yml`. Key differences:
- Build: `uv build --package unifi-protect-mcp`
- Job filter: `startsWith(github.event.release.tag_name, 'protect/v')`
- PyPI environment: `pypi` (same environment, add `protect/v*` tag rule)

- [ ] **Step 4: Commit**

```bash
git commit -m "ci(protect): add test, Docker, and PyPI publish workflows"
```

### Task 22: Update docker-compose.yml

**Files:**
- Modify: `docker/docker-compose.yml`

- [ ] **Step 1: Add Protect service**

Add `unifi-protect-mcp` service alongside existing network service. Port 3001, env_file, allowed hosts for 3001.

- [ ] **Step 2: Commit**

### Task 23: Create dev console

**Files:**
- Create: `apps/protect/devtools/dev_console.py`

- [ ] **Step 1: Adapt from Network's dev console**

Same REPL pattern. Key differences:
- Import from `unifi_protect_mcp.*`
- Protect-specific tool discovery
- Camera-focused example commands (list cameras, get snapshot, list events)

- [ ] **Step 2: Verify console starts**

```bash
cd apps/protect && make console
```

- [ ] **Step 3: Commit**

### Task 24: Docker build verification

- [ ] **Step 1: Build Docker image**

```bash
cd apps/protect && make docker
```

- [ ] **Step 2: Test with env-file**

```bash
make docker-run
```

- [ ] **Step 3: Test docker-compose**

```bash
docker compose -f docker/docker-compose.yml up --build
```

Verify both network (3000) and protect (3001) services start.

---

## Chunk 8: PR 8 — Documentation

### Task 25: Write Protect README

**Files:**
- Rewrite: `apps/protect/README.md`

Clean quick-start README:
- What it is
- Install (uvx, pip, Docker)
- Configure (minimum env vars)
- Run
- Links to docs/

### Task 26: Write detailed docs

**Files:**
- Create: `apps/protect/docs/configuration.md`
- Create: `apps/protect/docs/permissions.md`
- Create: `apps/protect/docs/tools.md`
- Create: `apps/protect/docs/events.md` (event streaming guide + client compatibility)
- Create: `apps/protect/docs/troubleshooting.md`

The `events.md` guide should document:
- How event streaming works (websocket → buffer → MCP resource subscription)
- How to subscribe from an MCP client
- Which clients support resource subscriptions (research during implementation)
- Fallback polling via `protect_recent_events` tool
- Configuration options (buffer size, TTL, confidence threshold)

### Task 27: Update root README status table

Update the server status table in the root `README.md`:

| Server | Status | Tools | Package |
|--------|--------|-------|---------|
| Network | Stable | 91 | `unifi-network-mcp` |
| **Protect** | **Stable** | **~40** | **`unifi-protect-mcp`** |
| Access | Planned | — | — |

### Task 28: Update root docs

- Update `docs/ARCHITECTURE.md` with Protect app description and `resources/` pattern
- Update `CONTRIBUTING.md` with Protect development workflow
- Update `CLAUDE.md` to reference Protect patterns where relevant

### Task 29: Final verification

- [ ] **Step 1: Full test suite across all packages**

```bash
make test
```

- [ ] **Step 2: Lint and format**
- [ ] **Step 3: Regenerate manifest, verify no diffs**
- [ ] **Step 4: Docker build and smoke test**
- [ ] **Step 5: Docker compose with both services**

After all verifications pass: tag `protect/v0.1.0`, publish, announce.
