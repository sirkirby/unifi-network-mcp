# UniFi Access MCP Server — Phase 3 Design Spec

**Date:** 2026-03-17
**Status:** Approved
**Scope:** Phase 3 — UniFi Access MCP server with ~28 tools, dual-path auth, real-time event streaming
**Parent plan:** [unified-mcp-idea.md](../../plans/unified-mcp-idea.md)
**Depends on:** Phase 1 (monorepo, shared packages), Phase 2 (Protect — pattern reference)

---

## Context

Phase 1 established the monorepo and shared packages. Phase 2 built the Protect server and proved the shared infrastructure works for new servers. Phase 3 adds the third and final MCP server — UniFi Access — covering door locks, access policies, credentials, visitors, and activity logs.

Access differs from Network and Protect in two key ways:
1. No established Python library with full coverage — `py-unifi-access` exists but covers a subset
2. The API requires a dual-path auth approach: API key for the official endpoints, session auth via proxy for the private API

---

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Library | `py-unifi-access` v1.1.1 | Async, WebSocket support, Pydantic models. Same author as Home Assistant integration. |
| Auth model | Dual path: API key (port 12445) + proxy session (port 443) | API key covers official endpoints; proxy session covers private API for full feature set |
| Connection manager | Thin wrapper with dual path (~150-200 lines) | Try API key first, fall back to proxy session. Both can coexist. |
| Tool auth routing | Per-tool `auth=` annotation | `either`, `local_only`, or `api_key_only` per tool. Manager routes to appropriate path. |
| Event streaming | Same pattern as Protect | EventBuffer + MCP resource subscription + polling tool |
| Tool naming | `access_` prefix | Consistent with Protect's `protect_` prefix. MCP server namespacing handles disambiguation. |
| Permissions | Read=true, all mutations opt-in, delete denied | `access_unlock_door` is a real-world physical action — must require explicit opt-in |
| Deployment | Separate Docker image (`unifi-access-mcp`) on port 3002 | Independent versioning, third service in docker-compose |
| Versioning | Prefixed tags (`access/v0.1.0`) | Same pattern as Network and Protect |

---

## Repository Structure

```
apps/access/
├── pyproject.toml                    # Package: unifi-access-mcp
├── src/
│   └── unifi_access_mcp/
│       ├── __init__.py
│       ├── main.py
│       ├── bootstrap.py              # UNIFI_ACCESS_* env vars > UNIFI_* fallback
│       ├── runtime.py
│       ├── tool_index.py
│       ├── categories.py             # ACCESS_CATEGORY_MAP, TOOL_MODULE_MAP
│       ├── schemas.py
│       ├── validators.py
│       ├── config/
│       │   └── config.yaml
│       ├── managers/
│       │   ├── connection_manager.py # Dual path: py-unifi-access + proxy session
│       │   ├── door_manager.py       # Doors, locks, unlock, door groups
│       │   ├── policy_manager.py     # Access policies and schedules
│       │   ├── credential_manager.py # NFC cards, PINs, keyfobs
│       │   ├── visitor_manager.py    # Visitor management
│       │   ├── event_manager.py      # Events, access logs, WebSocket buffer
│       │   ├── device_manager.py     # Hubs, readers, hardware
│       │   └── system_manager.py     # System info, health
│       ├── tools/
│       │   ├── doors.py              # ~6 tools
│       │   ├── policies.py           # ~4 tools
│       │   ├── credentials.py        # ~4 tools
│       │   ├── visitors.py           # ~3 tools
│       │   ├── events.py             # ~5 tools
│       │   ├── devices.py            # ~3 tools
│       │   └── system.py             # ~3 tools
│       ├── resources/
│       │   └── events.py             # MCP subscribable resource
│       └── tools_manifest.json
├── tests/
│   ├── conftest.py
│   └── unit/
├── devtools/
│   └── dev_console.py
├── scripts/
│   └── generate_tool_manifest.py
├── docs/
│   ├── configuration.md
│   ├── permissions.md
│   ├── tools.md
│   ├── events.md
│   └── troubleshooting.md
├── Dockerfile
├── Makefile
└── README.md
```

---

## Connection Manager (Dual Path)

~150-200 lines. The most novel piece for Access.

### Architecture

```
AccessConnectionManager
  ├── Path 1: py-unifi-access (port 12445, API key)
  │     └── client = UnifiAccessApiClient(host, api_key, session)
  │         └── Used for: doors, events, WebSocket
  │
  └── Path 2: Proxy session (port 443, username/password)
        └── Session auth via /api/auth/login → cookie + CSRF
            └── Requests go to /proxy/access/api/v2/...
            └── Used for: endpoints py-unifi-access doesn't cover
```

### Initialization Flow

1. If API key configured → try `py-unifi-access` authenticate on port 12445
2. If that succeeds → `_api_client` available as primary path
3. If that fails or no API key → log warning (not fatal)
4. If local credentials configured → establish proxy session via `/api/auth/login`
5. Proxy session maintained with cookie + CSRF token (details below)
6. Both paths can coexist — tools route based on `auth=` annotation
7. If neither path succeeds → fail with clear error listing what was tried

**Startup flexibility:** At least one auth path must succeed. API-key-only (no username/password) is allowed if `py-unifi-access` auth works. Local-only (no API key) is allowed and is the expected common case given the current auth status. Both configured is ideal.

### Proxy Session Lifecycle

The proxy session reuses the same auth flow as the Network server (`/api/auth/login` → cookie + CSRF):

- **Login:** POST `/api/auth/login` with `{"username": "...", "password": "..."}` → response includes `Set-Cookie: TOKEN=<jwt>` and `x-updated-csrf-token` header
- **CSRF token:** Extracted from `x-updated-csrf-token` response header on login. Included as `X-CSRF-Token` header on all subsequent requests.
- **Session expiration:** Detected by 401 response on any request. On 401, re-login automatically (one retry), then re-execute the failed request.
- **Concurrent safety:** Use `asyncio.Lock` around the re-login flow to prevent multiple simultaneous re-authentications.
- **Cookie jar:** `aiohttp.CookieJar(unsafe=True)` on the session, same as Network.

### Auth Fallback Behavior for `either` Tools

For tools marked `auth="either"`: if the API key client is configured and available, use it. If not configured or unavailable, use the proxy session. There is NO automatic per-request fallback from API key to proxy on 401 — the path is chosen at startup based on what's available. This avoids silent fallback confusion (consistent with Phase 1 spec: "no silent fallback").

### Contingency: API Key Auth Never Works

If `py-unifi-access` authentication cannot be made to work on the user's firmware:
- All tools operate via proxy session (`local_only` mode effectively)
- `auth="either"` annotations remain as forward-looking metadata
- WebSocket events may not be available (depends on whether proxy path supports WebSocket). If not, event tools fall back to REST polling via `/proxy/access/api/v2/` endpoints.
- Ship as proxy-only. This is still a fully functional server — same as how Network works without API key support today.

### Per-Tool Auth Routing

Tools declare their auth requirement:
- `auth="either"` — use API client if available, else proxy session
- `auth="local_only"` — proxy session only (private API endpoints)
- `auth="api_key_only"` — API client only (rare)

Default when `auth` is omitted: `local_only` (most Access tools need the private API).

### Configuration

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
```

---

## Event Streaming

Same proven pattern as Protect:

- **EventBuffer** ring buffer fed by `py-unifi-access` WebSocket subscription
- **MCP resource** at `access://events/stream` — clients subscribe, poll on notification
- **`access_recent_events` tool** — fast buffer read, no API call (primary mechanism)
- **Fallback**: REST API query via proxy session for historical events
- **WebSocket events**: door unlock, access granted, access denied, door position change, doorbell press

Same FastMCP push notification limitation applies — polling is the recommended approach.

---

## Tool Catalog (~28 tools)

### Doors (~6 tools)

| Tool | Action | Auth | Description |
|------|--------|------|-------------|
| `access_list_doors` | read | either | All doors from all hubs with status |
| `access_get_door` | read | either | Door details, lock state, position |
| `access_unlock_door` | update | either | Unlock with configurable duration (default 2s) |
| `access_lock_door` | update | local_only | Lock immediately |
| `access_get_door_status` | read | either | Current lock/position state |
| `access_list_door_groups` | read | local_only | Door groups/zones |

### Policies & Schedules (~4 tools)

| Tool | Action | Auth | Description |
|------|--------|------|-------------|
| `access_list_policies` | read | either | All access policies |
| `access_get_policy` | read | either | Policy details |
| `access_list_schedules` | read | local_only | Time-based unlock schedules |
| `access_update_policy` | update | local_only | Modify access policy (confirm pattern) |

### Credentials (~4 tools)

| Tool | Action | Auth | Description |
|------|--------|------|-------------|
| `access_list_credentials` | read | local_only | NFC cards, PINs, keyfobs |
| `access_get_credential` | read | local_only | Credential details, status, expiration |
| `access_create_credential` | create | local_only | Provision NFC card or PIN (confirm) |
| `access_revoke_credential` | delete | local_only | Disable/revoke credential (confirm, destructive) |

### Visitors (~3 tools)

| Tool | Action | Auth | Description |
|------|--------|------|-------------|
| `access_list_visitors` | read | either | All visitors |
| `access_create_visitor` | create | local_only | Create visitor with temporary access (confirm) |
| `access_delete_visitor` | delete | local_only | Remove visitor (confirm, destructive) |

### Events & Logs (~5 tools)

| Tool | Action | Auth | Description |
|------|--------|------|-------------|
| `access_list_events` | read | local_only | Access log entries with filters (time, door, user) |
| `access_get_event` | read | local_only | Single event details |
| `access_recent_events` | read | either | From WebSocket buffer (fast, no API call) |
| `access_subscribe_events` | read | either | Returns resource URI for MCP subscription |
| `access_get_activity_summary` | read | local_only | Aggregated stats (entries/exits per door/day) |

### Devices (~3 tools)

| Tool | Action | Auth | Description |
|------|--------|------|-------------|
| `access_list_devices` | read | either | Hubs, readers, all hardware |
| `access_get_device` | read | either | Device details, firmware, status |
| `access_reboot_device` | update | local_only | Reboot hub/reader (confirm, destructive) |

### System (~3 tools)

| Tool | Action | Auth | Description |
|------|--------|------|-------------|
| `access_get_system_info` | read | either | System overview, version |
| `access_get_health` | read | either | System health check |
| `access_list_users` | read | either | Users with access credentials |

---

## Permission Defaults

```yaml
permissions:
  default:
    read: true
    create: false
    update: false
    delete: false
  doors:
    read: true
    update: false
  policies:
    read: true
    update: false
  credentials:
    read: true
    create: false
    delete: false
  visitors:
    read: true
    create: false
    delete: false
  events:
    read: true
  devices:
    read: true
    update: false
  system:
    read: true
```

Same env var override pattern: `UNIFI_PERMISSIONS_DOORS_UPDATE=true`.

### ACCESS_CATEGORY_MAP

```python
ACCESS_CATEGORY_MAP = {
    "door": "doors",
    "policy": "policies",
    "schedule": "policies",
    "credential": "credentials",
    "visitor": "visitors",
    "event": "events",
    "device": "devices",
    "system": "system",
    "user": "system",
}
```

---

## Build & Deployment

### pyproject.toml

```
name = "unifi-access-mcp"
dependencies: unifi-core, unifi-mcp-shared, mcp[cli], py-unifi-access, aiohttp, pyyaml, python-dotenv, omegaconf
version: hatch-vcs with tag_regex matching access/v*
entry point: unifi-access-mcp = "unifi_access_mcp.main:main"
```

### CI Workflows

| Workflow | Triggers | Purpose |
|----------|----------|---------|
| `test-access.yml` | push to main, PRs | Run Access tests |
| `docker-access.yml` | push to main, `access/v*` tags | Build `ghcr.io/sirkirby/unifi-access-mcp` |
| `publish-access.yml` | GitHub release with `access/v*` tag | Publish to PyPI |

### Docker

- Separate image: `ghcr.io/sirkirby/unifi-access-mcp`
- Port 3002 (Network=3000, Protect=3001)
- Added to `docker/docker-compose.yml` as third service

### docker-compose.yml addition

```yaml
  unifi-access-mcp:
    build:
      context: ..
      dockerfile: apps/access/Dockerfile
    env_file:
      - ../.env
    environment:
      - UNIFI_MCP_HTTP_ENABLED=true
      - UNIFI_MCP_HTTP_TRANSPORT=streamable-http
      - UNIFI_MCP_HOST=0.0.0.0
      - UNIFI_MCP_PORT=3002
      - UNIFI_MCP_ALLOWED_HOSTS=localhost,localhost:3002,127.0.0.1,127.0.0.1:3002,host.docker.internal,host.docker.internal:3002
    ports:
      - "3002:3002"
    restart: unless-stopped
    container_name: unifi-access-mcp
```

### Root updates

- `.env.example`: Add `UNIFI_ACCESS_*` variables
- Root `Makefile`: Add `access-*` targets, update aggregate targets
- Root `README.md`: Update status table (Access: Beta)

---

## PR Sequencing

Each PR leaves tests green. No release until all 8 PRs land.

| PR | Scope | Risk |
|----|-------|------|
| **1** | App scaffold (directories, config, stubs) | Low |
| **2** | Connection manager (dual path) + system tools | **High** — novel dual-path auth, debugging against live instance |
| **3** | Door tools (list, get, unlock, lock, status, groups) | Medium |
| **4** | Event tools + WebSocket buffer + MCP resource | Medium (proven pattern) |
| **5** | Policy + credential + visitor tools | Low-medium |
| **6** | Device tools + remaining tools | Low |
| **7** | CI, Docker, docker-compose, dev console | Low |
| **8** | Documentation + final verification | Low |

After PR 8: tag `access/v0.1.0`, publish to PyPI, push Docker image, update root README.

---

## API Research Findings

### Confirmed Endpoints (port 12445)

Return 401 (exist, need auth) not 404:
- `/api/v1/developer/doors`
- `/api/v1/developer/users`
- `/api/v1/developer/access_policies`
- `/api/v1/developer/devices`
- `/api/v1/developer/visitors`

### Auth Status

- **API key on port 12445**: 401 with all tested keys. `py-unifi-access` library also gets 401. May need super admin credentials or specific firmware version. Library works for Home Assistant users — likely a permission/config issue.
- **Proxy session on port 443**: Works in browser with admin session cookie. `/proxy/access/api/v2/...` confirmed functional.
- **Access internal codename**: "Apollo" (`view:controller:apollo` scope)

### Implementation Strategy

1. Try `py-unifi-access` auth during `initialize()` — if it works, great
2. If not, fall back to proxy session (login → cookie → `/proxy/access/api/v2/`)
3. Reverse-engineer additional proxy endpoints as needed during development
4. User's live Access instance at `10.29.13.23:12445` (UNVR, same host as Protect)

---

## What's NOT in Phase 3

- **Full private API reverse engineering** — ship what works, expand later
- **Cross-server orchestration** — "unlock door when person detected on camera" (future Agent SDK work)
- **Multi-site Access** — single controller per server instance
- **Intercom/talk features** — separate product, out of scope

### Implementation Notes

- **`access_unlock_door`** is the highest-risk tool — physical real-world action. Confirm pattern required, `destructiveHint=true`. The `update` action type is used (consistent with Protect's `reboot_camera`) since Access doesn't have a separate `control` action in the permission system. The mutation is gated by `UNIFI_PERMISSIONS_DOORS_UPDATE=true`.
- If `py-unifi-access` WebSocket fails (auth issue), event tools fall back to REST API polling via proxy session. If WebSocket is unavailable, the event buffer stays empty and `access_recent_events` returns an empty list with a clear message.
- Parameter descriptions (`Annotated[..., Field(description=...)]`) on all tools from day one — learned from Phase 2.
- Same `SETUPTOOLS_SCM_PRETEND_VERSION` workaround in CI until first `access/v*` tag exists.
- **Missing from file tree but needed:** `utils/diagnostics.py`, `utils/config_helpers.py`, `validator_registry.py`, `jobs.py` — same modules as Protect. Create during scaffold (PR 1).
- **Config `server:` section** not shown in spec but identical to Protect's (host, port, log_level, tool_registration_mode, http, diagnostics). Copy from Protect's `config.yaml`.
- **`access.api_port` config** (12445) is a new pattern — flows into `AccessConnectionManager.__init__` as the port for `py-unifi-access`. The `unifi.port` (443) is for the proxy session.
- **No MCP image/media resources** for Access — only `resources/events.py`. Access is physical access control, not video.
- **Root `.env.example`**: Add `UNIFI_ACCESS_*` variables. Also add `UNIFI_PROTECT_*` if missing (Phase 2 debt).
