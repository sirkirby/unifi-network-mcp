# UniFi Access MCP Server — Phase 3 Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a new UniFi Access MCP server with ~28 tools, dual-path auth (API key + proxy session), and real-time event streaming.

**Architecture:** New server at `apps/access/` following the proven Protect pattern. Uses `py-unifi-access` for API key auth (port 12445) with proxy session fallback (port 443) for private API endpoints. EventBuffer + MCP resource subscription for real-time events.

**Tech Stack:** Python 3.13+, FastMCP, py-unifi-access, aiohttp, OmegaConf, uv workspaces, hatch-vcs, ruff, pytest

**Spec:** `docs/superpowers/specs/2026-03-17-unifi-access-mcp-design.md`

**Reference:** `apps/protect/` (follow its patterns exactly, adapting for Access-specific concerns)

---

## Chunk 1: PR 1 — App Scaffold

### Task 1: Create directory structure and package files

**Reference:** Copy the exact patterns from `apps/protect/` — same pyproject.toml structure, Makefile, Dockerfile, config.yaml layout. Adapt all names from `protect` to `access` and `unifi_protect_mcp` to `unifi_access_mcp`.

- [ ] **Step 1: Create directory scaffold**

```bash
mkdir -p apps/access/src/unifi_access_mcp/{config,managers,tools,resources,utils}
mkdir -p apps/access/{tests/unit,tests/integration,devtools,scripts,docs}
```

- [ ] **Step 2: Create `apps/access/pyproject.toml`**

Adapt from `apps/protect/pyproject.toml`:
- `name = "unifi-access-mcp"`
- Entry point: `unifi-access-mcp = "unifi_access_mcp.main:main"`
- Replace `uiprotect>=6.0.0` with `py-unifi-access>=1.1.1`
- `tag_regex` matches `access/v*` (with optional prefix like Protect)
- `known-first-party = ["unifi_access_mcp"]`
- Keep workspace sources for `unifi-mcp-shared` and `unifi-core`

- [ ] **Step 3: Create core module files**

Copy and adapt from Protect for each file:
- `__init__.py` — `"""UniFi Access MCP Server."""`
- `bootstrap.py` — `UNIFI_ACCESS_*` env var prefix with `UNIFI_*` fallback. `AccessSettings` dataclass. Logger name `"unifi-access-mcp"`.
- `categories.py` — `ACCESS_CATEGORY_MAP` and `TOOL_MODULE_MAP` with `tool_prefix="access_"`
- `tool_index.py` — Same as Protect, replace package name
- `runtime.py` — Manager factories for: door, policy, credential, visitor, event, device, system managers. `get_connection_manager()` stub.
- `main.py` — Same pattern as Protect, `ACCESS_CATEGORY_MAP`, server name `"unifi-access-mcp"`
- `jobs.py` — Same as Protect
- `schemas.py`, `validators.py`, `validator_registry.py` — Stubs
- `utils/diagnostics.py`, `utils/config_helpers.py` — Copy from Protect

- [ ] **Step 4: Create `config/config.yaml`**

Same `unifi:` and `server:` sections as Protect. Add Access-specific:
```yaml
unifi:
  host: ${oc.env:UNIFI_ACCESS_HOST,""}
  username: ${oc.env:UNIFI_ACCESS_USERNAME,""}
  password: ${oc.env:UNIFI_ACCESS_PASSWORD,""}
  port: ${oc.env:UNIFI_ACCESS_PORT,443}
  verify_ssl: ${oc.env:UNIFI_ACCESS_VERIFY_SSL,false}
  api_key: ${oc.env:UNIFI_ACCESS_API_KEY,""}

access:
  api_port: ${oc.env:UNIFI_ACCESS_API_PORT,12445}
  events:
    buffer_size: ${oc.env:ACCESS_EVENT_BUFFER_SIZE,100}
    buffer_ttl_seconds: ${oc.env:ACCESS_EVENT_BUFFER_TTL,300}
    websocket_enabled: ${oc.env:ACCESS_WEBSOCKET_ENABLED,true}

permissions:
  # ... (all Access categories, mutations default false)
```

Include full `server:` section copied from Protect's config.yaml.

- [ ] **Step 5: Create manager stubs**

8 manager files, each with a class stub:
- `connection_manager.py` → `AccessConnectionManager`
- `door_manager.py` → `DoorManager`
- `policy_manager.py` → `PolicyManager`
- `credential_manager.py` → `CredentialManager`
- `visitor_manager.py` → `VisitorManager`
- `event_manager.py` → `EventManager` + `EventBuffer`
- `device_manager.py` → `DeviceManager`
- `system_manager.py` → `SystemManager`

- [ ] **Step 6: Create tool module stubs, resource stubs, manifest**

Tool stubs: `doors.py`, `policies.py`, `credentials.py`, `visitors.py`, `events.py`, `devices.py`, `system.py`
Resources: `resources/__init__.py`, `resources/events.py`
Initial empty manifest: `tools_manifest.json`

- [ ] **Step 7: Create Makefile, Dockerfile, conftest.py, generate_tool_manifest.py**

All adapted from Protect:
- `Makefile` — full target set, `unifi-access-mcp` package name
- `Dockerfile` — same uv sync pattern, `unifi-access-mcp`
- `tests/conftest.py` — sys.path setup
- `scripts/generate_tool_manifest.py` — adapted for `unifi_access_mcp`
- `README.md` — placeholder

- [ ] **Step 8: Update root workspace**

- Root `Makefile`: Add Access to aggregate targets (`test`, `lint`, `format`, `manifest`)
- `uv sync` must succeed
- Root `.env.example`: Add `UNIFI_ACCESS_*` variables

- [ ] **Step 9: Verify and commit**

```bash
uv sync
make test   # All existing tests pass
make lint   # Access code lints clean
```

---

## Chunk 2: PR 2 — Connection Manager + System Tools (HIGH RISK)

### Task 2: Implement AccessConnectionManager (Dual Path)

**Files:**
- Create: `apps/access/src/unifi_access_mcp/managers/connection_manager.py`
- Create: `apps/access/tests/unit/test_connection_manager.py`

This is the novel piece — dual-path auth with automatic fallback.

- [ ] **Step 1: Implement the dual-path connection manager**

~150-200 lines. Key components:

```python
class AccessConnectionManager:
    def __init__(self, host, username, password, port, verify_ssl, api_key=None, api_port=12445):
        # Path 1: py-unifi-access client (API key, port 12445)
        self._api_client = None  # UnifiAccessApiClient
        self._api_key = api_key
        self._api_port = api_port

        # Path 2: Proxy session (local credentials, port 443)
        self._proxy_session = None  # aiohttp.ClientSession
        self._csrf_token = None
        self._auth_lock = asyncio.Lock()  # Concurrent safety for re-auth

        # State
        self._api_client_available = False
        self._proxy_available = False
```

**`initialize()` method:**
1. Try py-unifi-access auth if API key configured
2. Try proxy session login if credentials configured
3. At least one must succeed

**`_proxy_login()` method:**
- POST `/api/auth/login` with credentials
- Extract TOKEN cookie and CSRF token from response
- Store on session

**`_proxy_request(method, path, **kwargs)` method:**
- Make request via proxy path (`/proxy/access/api/v2/{path}`)
- On 401: re-login with `_auth_lock`, retry once

**Properties:**
- `api_client` — returns `UnifiAccessApiClient` or None
- `proxy_session` — returns authenticated `aiohttp.ClientSession`
- `has_api_client` / `has_proxy` — bool availability

- [ ] **Step 2: Write comprehensive tests**

Test: init, api_client auth success/failure, proxy login success/failure, proxy re-auth on 401, concurrent re-auth lock, dual path coexistence, neither path fails clearly.

Mock `UnifiAccessApiClient` and `aiohttp` responses.

- [ ] **Step 3: Wire into runtime.py**

Update `get_connection_manager()` to pass `api_port` from `config.access.api_port`.

- [ ] **Step 4: Commit**

### Task 3: Implement SystemManager + system tools

**Files:**
- Implement: `managers/system_manager.py`
- Implement: `tools/system.py`
- Create: `tests/unit/test_system.py`

3 tools: `access_get_system_info`, `access_get_health`, `access_list_users`

Each method tries `connection_manager.api_client` first (if available), falls back to `connection_manager.proxy_request()`.

Follow Protect's system manager pattern. All read-only with `ToolAnnotations(readOnlyHint=True)`.

All parameters use `Annotated[..., Field(description=...)]` from day one.

- [ ] **Step 1: Implement manager + tools + tests**
- [ ] **Step 2: Generate manifest, verify**
- [ ] **Step 3: Commit**

### Task 4: End-to-end verification (PR 2)

- [ ] **Step 1: Test against live Access instance (if auth works)**
- [ ] **Step 2: Full test suite, lint**
- [ ] **Step 3: Document auth findings in PR description**

---

## Chunk 3: PR 3 — Door Tools

### Task 5: Implement DoorManager

**Files:**
- Implement: `managers/door_manager.py`
- Create: `tests/unit/test_door_manager.py`

Methods:
- `list_doors()` — via `api_client.get_doors()` or proxy
- `get_door(door_id)` — single door details
- `unlock_door(door_id, duration=2)` — via `api_client.unlock_door()` or proxy POST
- `lock_door(door_id)` — proxy only (private API)
- `get_door_status(door_id)` — current lock/position state
- `list_door_groups()` — proxy only

For `either` auth tools: try API client, fall back to proxy.
For `local_only` tools: proxy only.

- [ ] **Step 1: Implement manager with dual-path routing**
- [ ] **Step 2: Write tests with mocked API client and proxy responses**
- [ ] **Step 3: Commit**

### Task 6: Implement door tools

**Files:**
- Implement: `tools/doors.py`
- Create: `tests/unit/test_door_tools.py`

6 tools with full `Annotated[..., Field(description=...)]` on all parameters:
- `access_list_doors` (read, either)
- `access_get_door` (read, either) — `door_id: Annotated[str, Field(description="Door UUID (from access_list_doors)")]`
- `access_unlock_door` (update, either, **destructiveHint=True**, confirm pattern) — `door_id`, `duration: Annotated[int, Field(description="Unlock duration in seconds (default 2)")] = 2`
- `access_lock_door` (update, local_only, confirm pattern)
- `access_get_door_status` (read, either)
- `access_list_door_groups` (read, local_only)

- [ ] **Step 1: Implement 6 tools with parameter descriptions**
- [ ] **Step 2: Write tests (success, error, confirm pattern)**
- [ ] **Step 3: Update manifest, verify, commit**

---

## Chunk 4: PR 4 — Events + Streaming

### Task 7: Implement EventBuffer

Same proven pattern as Protect. Copy `EventBuffer` from Protect's `event_manager.py` and adapt for Access event types.

- [ ] **Step 1: Implement EventBuffer with tests**
- [ ] **Step 2: Commit**

### Task 8: Implement EventManager

**Methods:**
- `start_listening()` — register callback on `py-unifi-access` WebSocket (if API client available)
- `_on_ws_message(msg)` — parse, add to buffer
- `list_events(start, end, door_id, user_id, limit)` — REST query via proxy
- `get_event(event_id)` — single event via proxy
- `get_recent_from_buffer(**filters)` — from EventBuffer
- `get_activity_summary(door_id, days)` — aggregated stats via proxy

**WebSocket fallback:** If API client not available, WebSocket events are unavailable. Log warning, `access_recent_events` returns empty with explanation.

- [ ] **Step 1: Implement EventManager**
- [ ] **Step 2: Write tests with mocked WebSocket messages**
- [ ] **Step 3: Commit**

### Task 9: Implement event stream MCP resource

Same pattern as Protect. Resource at `access://events/stream`.

- [ ] **Step 1: Implement resource**
- [ ] **Step 2: Commit**

### Task 10: Implement event tools

5 tools:
- `access_list_events` (read, local_only) — with time/door/user filters
- `access_get_event` (read, local_only)
- `access_recent_events` (read, either) — from buffer
- `access_subscribe_events` (read, either) — returns resource URI
- `access_get_activity_summary` (read, local_only)

- [ ] **Step 1: Implement tools with parameter descriptions**
- [ ] **Step 2: Wire WebSocket into main.py startup**
- [ ] **Step 3: Tests, manifest, commit**

---

## Chunk 5: PR 5 — Policies, Credentials, Visitors

### Task 11: Implement PolicyManager + policy tools

**Methods:** `list_policies()`, `get_policy(id)`, `list_schedules()`, `update_policy(id, changes)` / `apply_update_policy()`

4 tools: `access_list_policies`, `access_get_policy`, `access_list_schedules`, `access_update_policy`

- [ ] **Step 1: Implement manager + tools + tests**
- [ ] **Step 2: Commit**

### Task 12: Implement CredentialManager + credential tools

**Methods:** `list_credentials()`, `get_credential(id)`, `create_credential(type, data)` / `apply_create()`, `revoke_credential(id)` / `apply_revoke()`

4 tools: `access_list_credentials`, `access_get_credential`, `access_create_credential`, `access_revoke_credential`

- [ ] **Step 1: Implement manager + tools + tests**
- [ ] **Step 2: Commit**

### Task 13: Implement VisitorManager + visitor tools

**Methods:** `list_visitors()`, `create_visitor(name, access_start, access_end)` / `apply_create()`, `delete_visitor(id)` / `apply_delete()`

3 tools: `access_list_visitors`, `access_create_visitor`, `access_delete_visitor`

- [ ] **Step 1: Implement manager + tools + tests**
- [ ] **Step 2: Update manifest, full test suite, commit**

---

## Chunk 6: PR 6 — Device Tools

### Task 14: Implement DeviceManager + device tools

**Methods:** `list_devices()`, `get_device(id)`, `reboot_device(id)` / `apply_reboot()`

3 tools: `access_list_devices`, `access_get_device`, `access_reboot_device`

- [ ] **Step 1: Implement manager + tools + tests**
- [ ] **Step 2: Update manifest, full test suite, commit**

---

## Chunk 7: PR 7 — CI, Docker, Dev Console

### Task 15: Create CI workflows

Adapt from Protect workflows:
- `.github/workflows/test-access.yml` — with `SETUPTOOLS_SCM_PRETEND_VERSION` at workflow level
- `.github/workflows/docker-access.yml` — image `${{ github.repository_owner }}/unifi-access-mcp`, port 3002
- `.github/workflows/publish-access.yml` — tag filter `startsWith(github.event.release.tag_name, 'access/v')`

- [ ] **Step 1: Create 3 workflow files**
- [ ] **Step 2: Commit**

### Task 16: Update docker-compose.yml

Add Access as third service on port 3002.

- [ ] **Step 1: Add service to `docker/docker-compose.yml`**
- [ ] **Step 2: Commit**

### Task 17: Create dev console

Adapt from Protect. Access-specific commands: list doors, unlock door, list events, system info.

- [ ] **Step 1: Create `devtools/dev_console.py`**
- [ ] **Step 2: Verify `make console` starts**
- [ ] **Step 3: Commit**

### Task 18: Docker build verification

- [ ] **Step 1: `make docker`**
- [ ] **Step 2: `make docker-run` with env-file**
- [ ] **Step 3: Docker compose with all 3 services**

---

## Chunk 8: PR 8 — Documentation

### Task 19: Write Access README

Clean quick-start README following Protect pattern. Use `UNIFI_ACCESS_*` env vars.

### Task 20: Write detailed docs

- `configuration.md` — full env var table with Access-specific vars + `access.api_port`
- `permissions.md` — category defaults, unlock_door gating
- `tools.md` — all 28 tools with descriptions and auth annotations
- `events.md` — event streaming, WebSocket, polling fallback
- `troubleshooting.md` — auth debugging (API key vs proxy), connection issues

### Task 21: Update root docs

- Root `README.md`: Update status table (Access: Beta, 28 tools)
- `docs/ARCHITECTURE.md`: Add Access app, dual-path auth as new pattern
- `CONTRIBUTING.md`: Add Access development workflow
- `.env.example`: Ensure `UNIFI_ACCESS_*` and `UNIFI_PROTECT_*` vars present

### Task 22: Final verification

- [ ] **Step 1: `make test`** — all tests across all packages
- [ ] **Step 2: `make lint`**
- [ ] **Step 3: `make manifest`** — no diffs
- [ ] **Step 4: Docker build and smoke test**
- [ ] **Step 5: Docker compose with all 3 services running**

After all verifications pass: tag `access/v0.1.0`, publish to PyPI, push Docker image.
