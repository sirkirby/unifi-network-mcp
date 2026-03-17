# UniFi MCP Ecosystem — Design & Evolution Plan

## Summary

Evolve `sirkirby/unifi-network-mcp` from a standalone network MCP server into a multi-product UniFi ecosystem. Three specialized servers — Network, Protect, and Access — living in a Python monorepo (`sirkirby/unifi-mcp`) with shared infrastructure packages. Each server uses the proven lazy-loading meta-tool pattern, keeping token overhead minimal while covering the full UniFi product surface.

---

## Architecture Decision: Multi-Server Monorepo

**Why not one mega-server?** The UniFi products have fundamentally different API surfaces, lifecycles, and community libraries. Network is mature (80+ tools, aiounifi). Protect is reverse-engineered (pyunifiprotect). Access has a published API. Cramming them together creates coupling where none is needed — a Protect camera bug shouldn't block a Network firewall release.

**Why not fully separate repos?** Too much duplication. Auth logic, permission systems, lazy loading, YAML config, confirmation patterns — all of this is battle-tested in unifi-network-mcp and should be shared, not copied.

**The sweet spot: monorepo with shared packages.** Each server is independently versioned, tested, and deployed. Shared code lives in internal packages. Contributors pick a domain and go deep.

### Repository Layout

```
sirkirby/unifi-mcp/
├── apps/
│   ├── network/                    # Current unifi-network-mcp, migrated
│   │   ├── pyproject.toml          # Independent versioning
│   │   ├── src/unifi_network_mcp/
│   │   │   ├── main.py
│   │   │   ├── tools/              # 80+ existing tools
│   │   │   └── managers/           # 15 domain managers
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── README.md
│   ├── protect/                    # New — Phase 2
│   │   ├── pyproject.toml
│   │   ├── src/unifi_protect_mcp/
│   │   │   ├── main.py
│   │   │   ├── tools/
│   │   │   └── managers/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── README.md
│   └── access/                     # Future — Phase 3
│       └── (same structure)
├── packages/
│   ├── unifi-core/                 # Connection, auth, retry, error handling
│   │   ├── pyproject.toml
│   │   └── src/unifi_core/
│   │       ├── auth.py             # Dual auth: API key + local username/password
│   │       ├── connection.py       # Async connection pooling, reconnection
│   │       ├── retry.py            # Exponential backoff, rate limiting
│   │       └── exceptions.py       # Shared exception hierarchy
│   └── unifi-mcp-shared/          # MCP patterns reusable across servers
│       ├── pyproject.toml
│       └── src/unifi_mcp_shared/
│           ├── lazy_tools.py       # Meta-tool framework (tool_index, execute, batch)
│           ├── permissions.py      # YAML + env var permission system
│           ├── confirmation.py     # Preview/confirm for mutations
│           ├── config.py           # Shared YAML config loader
│           └── formatting.py       # Response formatting standards
├── docker/
│   └── docker-compose.yml          # Full local dev stack
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CONTRIBUTING.md
│   └── API_EVOLUTION.md
├── pyproject.toml                  # Workspace root
├── Makefile
└── README.md
```

### Migration Strategy: Rename, Don't Replace

The existing `sirkirby/unifi-network-mcp` has stars, issues, contributors, forks, and community trust. Preserve all of it.

**Approach: Rename the repo in-place.**

GitHub repo renames keep everything — stars, watchers, forks, issues, PRs, contributor history. GitHub also sets up an automatic 301 redirect from the old URL, so existing links, bookmarks, and MCP client configs continue working.

1. **Rename** `sirkirby/unifi-network-mcp` → `sirkirby/unifi-mcp` via GitHub Settings
2. Restructure into monorepo layout (`apps/network/`, `packages/`, etc.) over a series of PRs
3. Existing GitHub redirect handles `sirkirby/unifi-network-mcp` → `sirkirby/unifi-mcp` automatically
4. **PyPI package name stays** `unifi-network-mcp` — no breaking change for pip consumers
5. **Docker image name stays** `unifi-network-mcp` for the network app specifically
6. Announce the rename and ecosystem expansion in a GitHub release and README update
7. Update MCP client config examples (e.g., Claude Desktop `claude_desktop_config.json`) to reference new repo name — old references still resolve via redirect

**What stays the same for existing users:**

- All existing GitHub links redirect
- `pip install unifi-network-mcp` still works
- Docker images unchanged
- Tool names unchanged (`unifi_list_clients`, etc.)
- Config format unchanged

**What changes:**

- Repo URL (with automatic redirect from old URL)
- README reflects the broader ecosystem scope
- Directory structure evolves as shared packages are extracted

---

## Phase 1: Foundation & Network Server Evolution

**Goal:** Set up the monorepo, extract shared packages, add API key support, and improve the existing network server. No new products yet — just strengthening what exists.

### 1a. Extract Shared Packages

Pull these out of the network server into reusable packages:

**`packages/unifi-core`**

- `connection.py` — Async connection manager (from `managers/connection_manager.py`)
- `auth.py` — New dual auth strategy (see below)
- `retry.py` — Exponential backoff, reconnection logic
- `exceptions.py` — `UniFiConnectionError`, `UniFiAuthError`, `UniFiRateLimitError`

**`packages/unifi-mcp-shared`**

- `lazy_tools.py` — Meta-tool framework extracted from `utils/lazy_tool_loader.py` and `utils/meta_tools.py`
- `permissions.py` — YAML + env var permission system from `utils/permissions.py`
- `confirmation.py` — Preview/confirm pattern from `utils/confirmation.py`
- `config.py` — YAML config loader from `bootstrap.py`

The network server then imports from these packages instead of its own utils. No behavioral change — just structural.

### 1b. Dual Auth (API Key + Local)

The official UniFi API supports API keys but the surface is limited today. Local auth remains more capable. Support both with a clean fallback:

```python
# packages/unifi-core/src/unifi_core/auth.py

class UniFiAuth:
    """Dual authentication: API key preferred, local auth fallback."""

    def __init__(self, config: UniFiConfig):
        self.api_key = config.api_key  # From UNIFI_API_KEY env var
        self.username = config.username
        self.password = config.password
        self.strategy = "api_key" if self.api_key else "local"

    async def get_session(self) -> aiohttp.ClientSession:
        if self.strategy == "api_key":
            return self._api_key_session()
        return await self._local_auth_session()

    def _api_key_session(self) -> aiohttp.ClientSession:
        """API key via X-API-Key header."""
        return aiohttp.ClientSession(
            headers={"X-API-Key": self.api_key}
        )

    async def _local_auth_session(self) -> aiohttp.ClientSession:
        """Cookie-based session via username/password login."""
        # Existing aiounifi login flow
        ...
```

**Config addition:**

```yaml
unifi:
  api_key: ${UNIFI_API_KEY:}      # Optional — takes priority if set
  username: ${UNIFI_USERNAME}      # Fallback
  password: ${UNIFI_PASSWORD}      # Fallback
```

**Capability detection:** When using API keys, some endpoints may return 403. The auth layer should detect this and surface a clear message: "This operation requires local authentication. API key access is limited for this endpoint."

### 1c. Network Server Design Evaluation

Issues to address in the existing server:

1. **Tool taxonomy review** — 80+ tools is a lot. Are there redundant or rarely-used tools that could be consolidated? Run usage analytics if possible (OTEL).
2. **Error message quality** — Ensure every tool returns actionable error messages, not raw API errors.
3. **Idempotency** — Mutations should be safe to retry. Document which tools are idempotent.
4. **Rate limiting** — Add awareness of UniFi controller rate limits (especially for batch operations).
5. **Tool annotations** — Ensure all tools have proper MCP annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`).

### Phase 1 Timeline: ~4 weeks

| Week | Deliverable                                                  |
| ---- | ------------------------------------------------------------ |
| 1    | Rename repo to `unifi-mcp`, restructure into monorepo layout, move network code into `apps/network/` |
| 2    | Extract shared packages into `packages/`, update imports, all tests pass |
| 3    | Dual auth implementation, API key support                    |
| 4    | Design evaluation, tool annotations, docs, community ecosystem announcement |

---

## Phase 2: UniFi Protect MCP

**Goal:** Build `unifi-protect-mcp` as the second server in the monorepo. This is the most-requested community feature.

### API & Library Choice

**Library: pyunifiprotect (uiprotect)**

- Python, async-first, actively maintained
- Covers cameras, events, smart detection, recordings, websocket subscriptions
- Reverse-engineered API (no official Protect API exists)
- Consistent with all-Python decision

**Alternative evaluated:** hjdhjd/unifi-protect (Node.js) is more mature and feature-rich, but would break stack consistency and force a split ecosystem. pyunifiprotect is sufficient for MVP and can be extended.

### MVP Tool Scope (~35 tools)

**Cameras (10-12 tools)**

- `unifi_list_cameras` — List all cameras with status, model, firmware
- `unifi_get_camera` — Camera details (resolution, encoding, bitrate, recording mode)
- `unifi_update_camera` — Change name, recording mode, IR settings
- `unifi_get_snapshot` — Current frame from any camera (returns image data or URL)
- `unifi_get_event_thumbnail` — Snapshot from a specific event
- `unifi_ptz_control` — Pan/tilt/zoom for PTZ-capable cameras
- `unifi_reboot_camera` — Reboot with confirmation
- `unifi_toggle_recording` — Enable/disable recording with confirmation
- `unifi_get_camera_streams` — RTSP/RTSPS stream URLs

**Events & Smart Detection (10-12 tools)**

- `unifi_list_events` — Recent events with filters (type, camera, time range)
- `unifi_get_event` — Event details with metadata
- `unifi_list_smart_detections` — Person, vehicle, animal, package detections
- `unifi_get_motion_zones` — Motion/smart detection zone configuration
- `unifi_update_motion_zones` — Configure detection sensitivity and zones
- `unifi_subscribe_events` — Websocket event stream (real-time alerts)
- `unifi_acknowledge_event` — Mark event as reviewed

**Recordings (6-8 tools)**

- `unifi_list_recordings` — Recording segments by camera and time range
- `unifi_get_recording_status` — Storage usage, retention settings
- `unifi_export_clip` — Export video clip for a time range
- `unifi_get_timelapse` — Generate timelapse from recordings

**System (4-6 tools)**

- `unifi_system_info` — NVR details, storage, connected cameras
- `unifi_list_viewers` — Who has access to Protect
- `unifi_get_firmware_status` — Camera firmware versions, available updates
- `unifi_health_check` — Overall system health summary

### Architecture Patterns (Inherited from Network)

All of these come from the shared packages — no reimplementation:

- **Lazy loading** via meta-tools (`unifi_tool_index`, `unifi_execute`, `unifi_batch`)
- **Permission system** — YAML config controls which tool categories are enabled
- **Preview/confirm** — All mutations (reboot, toggle recording, update zones) require confirmation
- **Dual auth** — API key or local auth
- **Diagnostics** — Optional verbose logging for debugging

### Protect-Specific Considerations

1. **Image/video handling** — Snapshots and clips are binary data. Return URLs where possible, base64 only when explicitly requested. Consider a local cache for frequently-accessed thumbnails.
2. **Websocket events** — Protect's real-time event stream is one of its most powerful features. Design the subscription tool carefully — it should support filtering by event type and camera, and provide a clean way to unsubscribe.
3. **Smart detection confidence** — Include confidence scores in detection results so users can filter by reliability.
4. **Privacy zones** — Be mindful of privacy zone configurations. Don't expose tools that bypass privacy masks.

### Phase 2 Timeline: ~8 weeks

| Week | Deliverable                                                  |
| ---- | ------------------------------------------------------------ |
| 1-2  | Protect app scaffold, pyunifiprotect integration, connection manager |
| 3-4  | Camera management tools (list, get, snapshot, PTZ)           |
| 5-6  | Events, smart detection, recording tools                     |
| 7    | System tools, Docker, tests (85%+ coverage target)           |
| 8    | Documentation, README, community beta release                |

---

## Phase 3: Access, Ecosystem Composition & Future

### UniFi Access MCP

Access has a published API from Ubiquiti — the cleanest of the three products. Lower priority but straightforward to build.

**MVP scope (~25 tools):**

- Door/lock management (list, lock, unlock, status)
- Access policies and schedules
- NFC credential management
- Access logs and audit trail
- System health

**Timeline:** ~4 weeks after Protect stabilizes. The patterns will be fully proven by then, so this is mostly domain logic.

### Other UniFi Products to Consider

| Product                   | API Status         | Priority | Notes                                |
| ------------------------- | ------------------ | -------- | ------------------------------------ |
| **Connect (EV Charging)** | Unknown            | Low      | Niche use case                       |
| **Talk (Intercom)**       | Reverse-engineered | Medium   | Interesting with Protect integration |
| **LED (Lighting)**        | Limited            | Low      | Simple on/off/brightness             |
| **Identity (SSO)**        | Published          | Medium   | Could power auth across all servers  |

### The Orchestrator Question

You raised whether to go full ACP + Agent SDK for cross-server coordination. My take:

**Not yet. But design for it.**

Right now, a user running all three MCP servers in Claude Desktop (or any MCP client) already gets natural orchestration — they can ask "check my cameras and network health" and the LLM coordinates the calls. That covers 90% of use cases without any orchestrator code.

Where an orchestrator becomes valuable:

- **Automated workflows** — "When Protect detects a person at 2 AM, check if their MAC is on the network, and if not, lock the doors via Access"
- **Cross-product correlation** — "Show me network anomalies that coincide with camera offline events"
- **Scheduled operations** — "Every night at midnight, export today's Protect events and email a summary"

When the time comes, build this as an agent in Open Agent Kit using Claude Agent SDK. It consumes the three MCP servers as tool providers. ACP (now under Linux Foundation with Google A2A) is still stabilizing — not the right bet today. MCP + Claude Agent SDK is the stable, proven path, and you're already doing this with OpenClaw.

**Design for it now** by keeping the servers stateless and composable. No server should depend on another server running. Cross-product features belong in the orchestrator layer, not in individual servers.

---

## Shared Infrastructure Detail

### Permission Model (Unified Across Servers)

```yaml
# Each server's config.yaml follows the same pattern
permissions:
  default:
    read: true
    create: false
    update: false
    delete: false    # Always false by default

  # Network-specific
  firewall_policies:
    create: true
    update: true
  networks:
    create: false    # Risky — can disrupt traffic
    update: false

  # Protect-specific
  cameras:
    read: true
    update: false    # Changing recording mode is sensitive
  recordings:
    read: true
    export: true

  # Access-specific
  doors:
    read: true
    unlock: false    # Physical security — always require explicit permission
```

### Confirmation Pattern

All destructive or sensitive operations use the existing preview/confirm pattern:

```
User: "Reboot the front door camera"
→ unifi_reboot_camera(camera="front-door", confirm=false)
→ Returns preview: "This will reboot 'Front Door' (G4 Bullet). Recording will be interrupted for ~60 seconds."
→ User confirms
→ unifi_reboot_camera(camera="front-door", confirm=true)
→ Executes reboot
```

### Tool Naming Convention

**All tools use the `unifi_` prefix**, regardless of which server provides them. From the user's perspective, it's all one UniFi ecosystem — "use the UniFi tools to check my cameras and see if a firewall rule is blocking the stream" should just work without thinking about which product boundary they're crossing.

Namespace collisions are avoided through descriptive names, not product prefixes:

| Domain  | Example Tools                                                |
| ------- | ------------------------------------------------------------ |
| Network | `unifi_list_clients`, `unifi_toggle_firewall_rule`, `unifi_list_vlans` |
| Protect | `unifi_list_cameras`, `unifi_get_snapshot`, `unifi_list_smart_detections` |
| Access  | `unifi_list_doors`, `unifi_unlock_door`, `unifi_list_access_logs` |

**Why unified prefix?**

- Cross-product troubleshooting is common (network policy blocking a camera stream, camera monitoring an access-controlled door)
- Natural for agent interactions: "use the unifi tools to..." covers the whole suite
- The meta-tools (`unifi_tool_index`, `unifi_execute`, `unifi_batch`) already establish the `unifi_` convention
- Each server's `tool_index` returns its own tools — the LLM sees the full catalog when multiple servers are active

**Collision avoidance rules:**

- Network tools use infrastructure nouns: `clients`, `devices`, `vlans`, `firewall_rule`, `port_forward`
- Protect tools use surveillance nouns: `cameras`, `snapshot`, `recording`, `smart_detection`, `motion_zone`
- Access tools use physical security nouns: `doors`, `access_log`, `nfc_credential`, `access_schedule`
- If ambiguity arises, use `_network_`, `_protect_`, or `_access_` as an infix (e.g., `unifi_network_health`, `unifi_protect_health`, `unifi_access_health`)

---

## Community & Maintenance Strategy

### Contributor Model

You're a solo maintainer with a day job. The monorepo helps here — clear boundaries mean contributors can own a domain:

1. **CODEOWNERS** — You review all shared package changes. Product-specific tools can have community reviewers.
2. **Issue templates** — Separate templates per product (Network, Protect, Access, Shared).
3. **PR checklist** — Tools must include: docstring, input validation (Pydantic), test, permission annotation, confirmation for mutations.
4. **Good first issues** — Tag simple tool additions in Protect/Access as "good first issue" to attract contributors.

### Release Strategy

- **Network:** Continue current cadence (you know what works)
- **Protect:** Monthly releases during stabilization, then match Network
- **Access:** Same as Protect
- **Shared packages:** Release on demand when apps need changes

### Competitive Positioning

Existing Protect MCPs (itsablabla/unifi-protect-mcp at 19 tools, others) are basic. Your differentiation:

1. **Lazy loading** — No one else does this. Massive token savings.
2. **Permission system** — Production-ready access control.
3. **Confirmation pattern** — Safe mutations.
4. **Ecosystem coherence** — Network + Protect + Access under one roof.
5. **Community trust** — unifi-network-mcp already has the reputation.

---

## Risk & Mitigation

| Risk                                                 | Mitigation                                                   |
| ---------------------------------------------------- | ------------------------------------------------------------ |
| pyunifiprotect lags behind firmware updates          | Maintain a thin wrapper layer; contribute upstream; can fork if needed |
| Repo rename breaks existing users                    | GitHub auto-redirects old URL; PyPI/Docker names unchanged; announce in release notes |
| Solo maintainer bandwidth                            | Recruit co-maintainers for Protect/Access early, automate CI/CD, tight MVP scopes |
| Ubiquiti releases official Protect API               | Great problem to have — add official API support alongside reverse-engineered |
| Lazy loading doesn't scale past 100 tools per server | Already proven at 80 tools with 96% savings; unlikely to hit limits |

---

## Overall Timeline

| Phase                         | Duration    | Key Outcome                                                  |
| ----------------------------- | ----------- | ------------------------------------------------------------ |
| **Phase 1** — Foundation      | Weeks 1-4   | Monorepo live, shared packages extracted, API key support, design eval done |
| **Phase 2** — Protect         | Weeks 5-12  | unifi-protect-mcp MVP (35 tools), Docker, tests, community beta |
| **Phase 3** — Access + Future | Weeks 13-20 | unifi-access-mcp MVP (25 tools), ecosystem docs, orchestrator design |

**Total: ~20 weeks (5 months) for a production-quality three-product ecosystem.**

---

## Next Steps

1. **Rename** `sirkirby/unifi-network-mcp` → `sirkirby/unifi-mcp` via GitHub Settings
2. Restructure into monorepo layout over a series of PRs (apps/network, packages/)
3. Extract shared packages and verify all tests pass
4. Implement dual auth with API key support
5. Announce the ecosystem roadmap to the community (GitHub release + README)
6. Begin Protect server development