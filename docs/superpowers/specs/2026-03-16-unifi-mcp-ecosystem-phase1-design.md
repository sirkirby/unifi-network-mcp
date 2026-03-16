# UniFi MCP Ecosystem — Phase 1 Design Spec

**Date:** 2026-03-16
**Status:** Approved
**Scope:** Phase 1 — Monorepo migration, shared package extraction, dual auth, network server improvements
**Parent plan:** [unified-mcp-idea.md](../../plans/unified-mcp-idea.md)

---

## Context

`sirkirby/unifi-network-mcp` is a production MCP server with 91 tools, ~200 GitHub stars, active contributors, and growing community demand for UniFi Protect and Access MCP servers. Rather than building separate repos (duplicating battle-tested infrastructure) or one mega-server (coupling unrelated products), we're evolving into a monorepo with shared packages and independently versioned servers.

Phase 1 establishes the monorepo foundation. Phases 2 (Protect) and 3 (Access) are documented in the parent plan but will be designed separately once this foundation is proven.

---

## Decisions

These decisions were made during the brainstorming session and are binding for Phase 1.

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Repo rename timing | First step | GitHub 301 redirect handles old URLs. PyPI/Docker names unchanged. |
| Shared package granularity | Two packages: `unifi-core` + `unifi-mcp-shared` | Clean boundary: UniFi connectivity vs MCP patterns |
| Workspace tooling | `uv` workspaces | Already in use, mature workspace support |
| Migration strategy | Option C: structural move, then extraction | Avoids doing two things at once. Each PR has a clear gate. |
| `aiounifi` relationship | Wrap, don't replace | Battle-tested across multiple projects and Home Assistant |
| Meta-tool naming | Keep shared names (`unifi_tool_index`, etc.) | MCP server-level namespacing handles disambiguation |
| Auth model | Per-tool annotation, not global preference | Official and private APIs return different payloads per endpoint |
| Versioning | Prefixed git tags (`network/v0.5.0`) | Independent release cycles per server |
| Network improvements | Light touch only | Contributors have addressed many issues recently |
| Release timing | No tag until all 7 PRs land | Users on PyPI/Docker see one clean upgrade |

---

## Repository Structure

After Phase 1 completion:

```
sirkirby/unifi-mcp/
├── apps/
│   └── network/
│       ├── pyproject.toml           # Package: unifi-network-mcp
│       ├── src/
│       │   └── unifi_network_mcp/
│       │       ├── __init__.py
│       │       ├── main.py
│       │       ├── bootstrap.py
│       │       ├── runtime.py
│       │       ├── tool_index.py
│       │       ├── jobs.py
│       │       ├── schemas.py
│       │       ├── validators.py
│       │       ├── validator_registry.py
│       │       ├── config/
│       │       │   └── config.yaml
│       │       ├── managers/        # All 15 network managers
│       │       ├── tools/           # All 17 tool modules (91 tools)
│       │       └── utils/           # Network-specific only
│       │           ├── diagnostics.py
│       │           └── config_helpers.py
│       ├── tests/
│       ├── devtools/
│       ├── scripts/
│       ├── docs/
│       │   ├── configuration.md
│       │   ├── permissions.md
│       │   ├── tools.md
│       │   ├── transports.md
│       │   └── troubleshooting.md
│       ├── Dockerfile
│       ├── Makefile
│       └── README.md                # Quick-start entrypoint
├── packages/
│   ├── unifi-core/
│   │   ├── pyproject.toml
│   │   └── src/
│   │       └── unifi_core/
│   │           ├── __init__.py
│   │           ├── auth.py
│   │           ├── connection.py
│   │           ├── detection.py
│   │           ├── retry.py
│   │           └── exceptions.py
│   └── unifi-mcp-shared/
│       ├── pyproject.toml
│       └── src/
│           └── unifi_mcp_shared/
│               ├── __init__.py
│               ├── permissions.py
│               ├── confirmation.py
│               ├── lazy_tools.py
│               ├── meta_tools.py
│               ├── tool_loader.py
│               ├── config.py
│               └── formatting.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CONTRIBUTING.md
│   └── plans/
│       └── unified-mcp-idea.md
├── .well-known/
│   └── mcp-server.json
├── pyproject.toml                   # uv workspace root
├── Makefile                         # Top-level delegation
├── README.md                        # Ecosystem landing page
└── docker-compose.yml
```

---

## Package: `unifi-core`

Owns the "talk to a UniFi controller" concern. Any MCP server depends on it for authentication and base connectivity.

### Modules

**`auth.py`** — Dual auth strategy with per-tool routing.

- `AuthStrategy` protocol: contract that each app fulfills for local auth (`get_session() -> aiohttp.ClientSession`)
- `UniFiAuth` class: holds API key config + local auth adapter. Provides sessions by auth method.
- API key path: `X-API-Key` header on `aiohttp.ClientSession`. Implemented directly — no external library needed.
- Local auth path: delegates to the app's library (aiounifi, pyunifiprotect, custom aiohttp).
- Clear error when a tool requires an auth method that isn't configured.

**`detection.py`** — UniFi OS vs standalone/self-hosted controller detection.

- Extracted from the network server's existing controller type detection logic.
- Determines API path prefix (`/proxy/network/...` vs `/api/...`).
- All three servers need this — the path structure differs by controller type regardless of product.

**`connection.py`** — Base async connection primitives.

- Session lifecycle management, SSL configuration, host/port resolution, health checking.
- NOT a full connection manager. Each app extends this with library-specific logic.
- Network's `ConnectionManager` (600+ lines) stays in the network app and extends the base.

**`retry.py`** — Exponential backoff, configurable retry policies.

- Centralizes currently scattered/implicit retry logic.
- All three servers get consistent retry behavior.

**`exceptions.py`** — Shared exception hierarchy.

- `UniFiError` → `UniFiAuthError`, `UniFiConnectionError`, `UniFiRateLimitError`, `UniFiPermissionError`.
- Servers extend with domain-specific exceptions.

### Dependencies

```
aiohttp>=3.8.5
pyyaml>=6.0
```

Deliberately minimal. No `aiounifi`, no `mcp`, no `omegaconf`.

---

## Package: `unifi-mcp-shared`

Owns "how to build an MCP server the UniFi way." Reusable patterns all servers import.

### Modules

**`permissions.py`** — YAML + env var permission system.

- Extracted from `src/utils/permissions.py`.
- `CATEGORY_MAP` becomes configurable: each server passes its own category mappings at init.
- Core priority chain unchanged: env var > YAML > default section > hardcoded fallback.

**`confirmation.py`** — Preview/confirm pattern for mutations.

- Extracted from `src/utils/confirmation.py`. Already generic, minimal changes needed.

**`lazy_tools.py`** — Lazy/on-demand tool registration.

- Extracted from `src/utils/lazy_tool_loader.py`.
- `TOOL_MODULE_MAP` becomes a parameter. Each server provides its own map.

**`meta_tools.py`** — `tool_index`, `execute`, `batch` meta-tools.

- Extracted from `src/utils/meta_tools.py`.
- Manifest path and tool references made configurable via init.

**`tool_loader.py`** — Eager tool registration.

- Extracted from `src/utils/tool_loader.py`. Same generalization as lazy_tools.

**`config.py`** — Shared config loading.

- Extracted from `bootstrap.py`. OmegaConf loading, env var interpolation, logging setup.
- Each server provides its own `config.yaml`, shared machinery loads it.

**`formatting.py`** — Response formatting helpers.

- Enforces the `{"success": bool, "data": ...}` / `{"success": false, "error": ...}` contract as helpers.

### Generalization Pattern

Shared modules expose factory or init functions that accept server-specific config. Simple parameterization, not a plugin framework:

```python
from unifi_mcp_shared.permissions import PermissionChecker
from unifi_network_mcp.categories import NETWORK_CATEGORY_MAP

permissions = PermissionChecker(
    category_map=NETWORK_CATEGORY_MAP,
    config=config.permissions,
)
```

### Dependencies

```
mcp[cli]>=1.26.0,<2
omegaconf>=2.3.0
pyyaml>=6.0
```

---

## Dual Auth Implementation

### Per-Tool Auth Annotations

Tools declare their auth requirement via the existing decorator:

```python
@permissioned_tool(
    category="clients",
    action="read",
    auth="local_only",
    read_only=True,
)
async def unifi_list_clients(...):
    ...
```

Auth annotation values:
- `local_only` — requires username/password session (private API, richer payloads)
- `api_key_only` — only available via official API
- `either` — both auth methods return equivalent data

### Auth Flow

```
Tool invoked → check auth annotation
  ├── "local_only" → request local auth session from app's adapter
  ├── "api_key_only" → request API key session from unifi-core
  ├── "either" → use API key if configured, else local
  └── auth method not configured → clear error message
```

### Configuration

```yaml
unifi:
  api_key: ${oc.env:UNIFI_API_KEY,}     # Optional
  username: ${oc.env:UNIFI_USERNAME,}     # Required for local auth
  password: ${oc.env:UNIFI_PASSWORD,}     # Required for local auth
```

Both can be configured simultaneously. The server uses whichever each tool requires.

### Capability Detection

When a tool using API key auth hits a 403, the error message is explicit: "This operation requires local authentication. Set UNIFI_USERNAME and UNIFI_PASSWORD for full access." No silent fallback.

---

## Network App Migration

### Import Changes

| Before | After |
|--------|-------|
| `from src.managers.client_manager import ...` | `from unifi_network_mcp.managers.client_manager import ...` |
| `from src.utils.permissions import ...` | `from unifi_mcp_shared.permissions import ...` |
| `from src.utils.confirmation import ...` | `from unifi_mcp_shared.confirmation import ...` |
| (new) | `from unifi_core.auth import UniFiAuth` |
| (new) | `from unifi_core.detection import detect_controller_type` |

### What Stays the Same

- PyPI package name: `unifi-network-mcp`
- Docker image name
- All 91 tool names
- Config format and env var names (new: `UNIFI_API_KEY`)
- User-facing behavior — zero breaking changes for existing users
- Console script entry point: `unifi-network-mcp`

### Versioning

- `hatch-vcs` with prefixed tags: `network/v0.5.0`
- Each app independently versioned
- Shared packages versioned separately

---

## README & Documentation

### Root README (~100-150 lines)

- Hero: one-liner, badges, server status table
- What is this: 2-3 sentences
- Quick start: fastest path to running network server
- Server overview: table with links to app READMEs
- Configuration: common patterns, links to details
- Roadmap: brief paragraph + link to ecosystem plan
- Contributing + License

### Network README

Clean quick-start entrypoint. Links to `docs/` for everything detailed.

### Network `docs/`

- `configuration.md` — full config tables, env vars
- `permissions.md` — permission system deep dive
- `tools.md` — tool catalog (or auto-generated from manifest)
- `transports.md` — stdio, HTTP, SSE setup
- `troubleshooting.md` — common issues

### Other Docs

- Root `docs/ARCHITECTURE.md` — monorepo structure, how to add a server
- Root `docs/CONTRIBUTING.md` — updated for monorepo workflow
- `CLAUDE.md` — updated to reflect monorepo paths and patterns

---

## Light-Touch Network Improvements

### MCP Tool Annotations

Add `readOnlyHint`, `destructiveHint`, `idempotentHint` to all 91 tools via the decorator. Metadata only — no behavioral change.

### Error Message Audit

Quick pass through tool modules. Replace vague or raw exception messages with specific, actionable ones. Not a full rewrite — worst offenders only.

### CLAUDE.md Update

Reflect monorepo structure, new import paths, shared package patterns, and updated development workflow.

---

## PR Sequencing

Each PR leaves tests green. No release tag until all 7 land.

| PR | Scope | Risk |
|----|-------|------|
| **1** | Repo rename + monorepo scaffold (dirs, root pyproject.toml, placeholder packages) | Low — no code moves |
| **2** | Move network code into `apps/network/`, rewrite all imports | **High** — touches every file |
| **3** | Extract `unifi-mcp-shared` from network utils, generalize interfaces | Medium — interface design |
| **4** | Extract `unifi-core` (auth strategy, detection, connection base, retry, exceptions) | Medium — new abstractions |
| **5** | Dual auth integration (API key support, per-tool auth annotations, unifi-cli code) | Medium — new functionality |
| **6** | README overhaul + documentation restructure | Low — content only |
| **7** | MCP tool annotations + error audit + CLAUDE.md update | Low — metadata + copy |

After PR 7: tag `network/v0.5.0` (or appropriate version), publish to PyPI, push Docker image, announce ecosystem.

---

## What's NOT in Phase 1

Preserved in the parent plan for future phases:

- **Phase 2:** UniFi Protect MCP server (~35 tools, pyunifiprotect/uiprotect)
- **Phase 3:** UniFi Access MCP server (~25 tools, custom aiohttp client on published API)
- **Orchestrator:** Cross-product agent using Claude Agent SDK (design for it, don't build it yet)
- **Rate limiting:** Valuable but belongs in `unifi-core` once the package is proven
- **Tool taxonomy review:** Separate initiative, doesn't block Protect/Access
- **OTEL/usage analytics:** Future observability work

All servers will share `unifi-core` and `unifi-mcp-shared`. The monorepo structure supports adding `apps/protect/` and `apps/access/` as vertical slices following the same patterns.
